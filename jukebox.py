#!/usr/bin/env python3
"""scoremill jukebox — play a folder of scoremill scores.

Renders each scoremill script to MIDI once, then plays the results to a
MIDI output. With no flag it opens the GUI; the flags
below are headless, for agents and automation.

  python jukebox.py                 # GUI
  python jukebox.py --list          # print the playlist and exit
  python jukebox.py --track 3       # play one track to the end and exit
  python jukebox.py --all           # play the whole playlist in order
  python jukebox.py --dir myscores --port "FluidSynth"

Network play (jukebox on one host, instrument on another; the far host
needs no MIDI hardware or backend):

  python jukebox.py --forward       # on the host with the instrument
  python jukebox.py --remote HOST   # stream playback there

The forwarder re-selects the instrument on each connection, so it can
start before the instrument is powered on. Rendering runs each script
with the host Python; a script writes its .mid next to itself, so one
script may contribute several tracks. Requires mido, and python-rtmidi
for real output ports.
"""
import glob
import json
import os
import socket
import subprocess
import sys
import threading
import time

import mido

DEFAULT_FORWARD_PORT = 13949

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "examples")


def tempo_factor(pct):
    """Playback speed multiplier for a tempo percentage (100 = native)."""
    return max(0.1, min(4.0, pct / 100.0))


def pretty_title(path):
    """A display title from a .mid filename: underscores to spaces,
    words capitalized, a leading numeric index dropped."""
    stem = os.path.splitext(os.path.basename(path))[0]
    words = [w for w in stem.replace("-", "_").split("_") if w]
    if words and words[0].isdigit():
        words = words[1:]
    return " ".join(w.capitalize() for w in words) or stem


# ── rendering ────────────────────────────────────────────────
def render_scores(src_dir, log=lambda s: None, force=False):
    """Run each *.py in src_dir so it writes its MIDI (the scoremill
    contract), then return the sorted list of .mid files present.
    Rendering is idempotent: a script simply overwrites its own output,
    and one script may write several files. A stamp file remembers each
    script's mtime at its last render, so a repeat launch with nothing
    edited renders nothing; pass force=True to render regardless.
    Returns (midi_paths, errors)."""
    errors = []
    stamp_path = os.path.join(src_dir, ".render_stamp.json")
    stamps = {}
    if not force:
        try:
            with open(stamp_path, "r", encoding="utf-8") as fh:
                stamps = json.load(fh)
        except (OSError, ValueError):
            stamps = {}
    have_midi = bool(glob.glob(os.path.join(src_dir, "*.mid")))
    scripts = sorted(glob.glob(os.path.join(src_dir, "*.py")))
    names = {os.path.basename(s) for s in scripts}
    stamps = {k: v for k, v in stamps.items() if k in names}
    for script in scripts:
        name = os.path.basename(script)
        mtime = os.path.getmtime(script)
        if not force and have_midi and stamps.get(name) == mtime:
            continue                # this exact version rendered before
        log(f"rendering {name} ...")
        try:
            subprocess.run([sys.executable, script],
                           cwd=src_dir, capture_output=True, text=True,
                           timeout=120, check=True)
        except (subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as e:
            errors.append(f"{name}: {e}")
        stamps[name] = mtime        # error too: retry only when it changes
    try:
        with open(stamp_path, "w", encoding="utf-8") as fh:
            json.dump(stamps, fh)
    except OSError:
        pass
    midis = sorted(glob.glob(os.path.join(src_dir, "*.mid")))
    return midis, errors


# ── network transport ────────────────────────────────────────
class NetworkOutput:
    """A stand-in for a mido output port that streams each message as
    raw MIDI bytes over TCP to a forwarder (see run_forwarder). Lets the
    jukebox run on a machine with no MIDI hardware and play through an
    instrument attached to another host — the forwarder just relays."""

    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.port_name = f"{host}:{port} (network forwarder)"

    def send(self, msg):
        try:
            self.sock.sendall(bytes(msg.bytes()))
        except OSError:
            pass

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def run_forwarder(bind_host, bind_port, piano_port=None):
    """Relay MIDI bytes from a network client to a local instrument.
    Re-selects the output on every new connection, so turning the
    instrument on between sessions just works, and releases all notes
    when a client disconnects."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((bind_host, bind_port))
    srv.listen(1)
    print(f"forwarder listening on {bind_host}:{bind_port} (Ctrl-C to stop)",
          flush=True)
    try:
        while True:
            conn, addr = srv.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            out = None
            count = 0
            try:
                names = mido.get_output_names()
                if not names:
                    print(f"client {addr[0]}: no MIDI output ports here — "
                          f"is the instrument connected?", flush=True)
                    continue
                target = None
                if piano_port:
                    target = next((n for n in names
                                   if piano_port.lower() in n.lower()), None)
                    if target is None:
                        print(f"client {addr[0]}: no port matching "
                              f"{piano_port!r}; available: {names}",
                              flush=True)
                if target is None:
                    target = Player._auto_select(names)
                loop = "through" in target.lower()
                print(f"client {addr[0]} -> {target}"
                      + (" (loopback: silent)" if loop else ""), flush=True)
                out = mido.open_output(target)
                parser = mido.Parser()
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    parser.feed(data)
                    for msg in parser:
                        out.send(msg)
                        count += 1
            except KeyboardInterrupt:
                raise
            except Exception as e:
                # One bad connection or a busy/absent port must not
                # bring the forwarder down; report and keep listening.
                print(f"client {addr[0]}: {e}", flush=True)
            finally:
                if out is not None:
                    try:
                        for ch in range(16):
                            out.send(mido.Message("control_change",
                                                  channel=ch,
                                                  control=64, value=0))
                            out.send(mido.Message("control_change",
                                                  channel=ch,
                                                  control=123, value=0))
                        out.close()
                    except Exception:
                        pass
                conn.close()
                print(f"client {addr[0]} disconnected ({count} messages)",
                      flush=True)
    except KeyboardInterrupt:
        print("\nforwarder stopped")
    finally:
        srv.close()


# ── playback engine ──────────────────────────────────────────
class Player:
    """Streams a MIDI file to an output port in a background thread,
    applying live tempo, channel volume, and a voice override, and
    releasing every note and pedal on stop or finish."""

    HINTS = ("piano", "keyboard", "digital", "synth", "fluid", "usb")

    def __init__(self, port=None, on_finish=None, remote=None):
        if remote is not None:
            self.out = NetworkOutput(*remote)
            self.port_name = self.out.port_name
        else:
            names = mido.get_output_names()
            if not names:
                raise RuntimeError("no MIDI output ports available "
                                   "(install python-rtmidi, or start a synth)")
            if port:
                match = next((n for n in names
                              if port.lower() in n.lower()), None)
                if match is None:
                    raise RuntimeError(f"no output matching {port!r}; "
                                       f"available: {names}")
            else:
                match = self._auto_select(names)
            self.port_name = match
            if "through" in match.lower():
                print(f"warning: playing to {match!r}, a MIDI loopback: "
                      f"no sound unless a synth or instrument is chained to "
                      f"it. Connect an instrument, or pass --port.",
                      file=sys.stderr)
            self.out = mido.open_output(match)
        self.on_finish = on_finish
        self.tempo_pct = 100
        self.volume = 100
        self.voice = 0
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.now = None

    @classmethod
    def _auto_select(cls, names):
        """Prefer a real instrument: an output whose name hints at a
        keyboard or synth, else the first non-loopback, else whatever
        is left (a loopback, which the caller warns about)."""
        real = [n for n in names if "through" not in n.lower()]
        for n in real:
            if any(h in n.lower() for h in cls.HINTS):
                return n
        return real[0] if real else names[0]

    # -- controls --
    def set_tempo(self, pct):
        self.tempo_pct = max(25, min(400, int(pct)))

    def set_volume(self, vol):
        self.volume = max(0, min(127, int(vol)))
        for ch in range(16):
            self.out.send(mido.Message("control_change", channel=ch,
                                       control=7, value=self.volume))

    def set_voice(self, program):
        self.voice = max(0, min(127, int(program)))
        for ch in range(16):
            self.out.send(mido.Message("program_change", channel=ch,
                                       program=self.voice))

    def _panic(self):
        for ch in range(16):
            self.out.send(mido.Message("control_change", channel=ch,
                                       control=64, value=0))    # sustain off
            self.out.send(mido.Message("control_change", channel=ch,
                                       control=123, value=0))   # all notes off

    def stop(self):
        self._stop.set()
        t = self._thread
        # A natural finish calls on_finish -> play -> stop from inside the
        # player thread; never join the current thread with itself.
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=2.0)
        self._panic()
        self.now = None

    def play(self, path, title=None):
        self.stop()
        self._stop.clear()
        self.now = title or pretty_title(path)
        self._thread = threading.Thread(target=self._run, args=(path,),
                                        daemon=True)
        self._thread.start()

    def _run(self, path):
        try:
            mid = mido.MidiFile(path)
        except Exception:
            self.now = None
            return
        for ch in range(16):
            self.out.send(mido.Message("control_change", channel=ch,
                                       control=7, value=self.volume))
        self.set_voice(self.voice)
        try:
            for msg in mid:                       # msg.time is delta seconds
                if self._stop.is_set():
                    break
                if msg.time:
                    end = time.monotonic() + msg.time / tempo_factor(
                        self.tempo_pct)
                    while True:
                        remaining = end - time.monotonic()
                        if remaining <= 0 or self._stop.is_set():
                            break
                        time.sleep(min(remaining, 0.02))
                if self._stop.is_set():
                    break
                if msg.is_meta:
                    continue
                if msg.type == "program_change":
                    continue                      # our voice override wins
                self.out.send(msg)
        finally:
            self._panic()
        if not self._stop.is_set():
            self.now = None
            if self.on_finish:
                self.on_finish()

    def close(self):
        self.stop()
        self.out.close()


def build_tracks(src_dir, force=False):
    midis, errors = render_scores(
        src_dir, log=lambda s: print(s, file=sys.stderr), force=force)
    for e in errors:
        print(f"warning: {e}", file=sys.stderr)
    return [(pretty_title(m), m) for m in midis]


def scan_library(root):
    """Grouped tracks from a directory of existing MIDI files:
    [(group, sub, title, path)]. The first folder under `root` is the
    group, the second the sub-playlist; files directly in `root` group
    under ''. No rendering, just a walk."""
    root = os.path.abspath(root)
    tracks = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        rel = os.path.relpath(dirpath, root)
        parts = [] if rel == os.curdir else rel.split(os.sep)
        group = parts[0] if parts else ""
        sub = parts[1] if len(parts) > 1 else ""
        for fn in sorted(filenames):
            if fn.lower().endswith((".mid", ".midi")):
                tracks.append((group, sub, pretty_title(fn),
                               os.path.join(dirpath, fn)))
    return tracks


def _parse_hostport(s, default_port):
    host, _, p = s.partition(":")
    return host, int(p) if p else default_port


# ── GUI (tkinter; imported lazily when the window opens) ──────
BG, BG2, BG3 = "#1e1e2e", "#282840", "#313150"
FG, DIM, ACCENT = "#e0e0e0", "#888899", "#3b5998"
GREEN, RED, YELLOW = "#4ecca3", "#e94560", "#ffd700"

# General-MIDI voices offered in the Voice picker (program, label).
VOICES = [
    (0, "Grand Piano"), (1, "Bright Piano"), (2, "Electric Grand"),
    (4, "Electric Piano 1"), (5, "Electric Piano 2"), (6, "Harpsichord"),
    (7, "Clavinet"), (8, "Celesta"), (10, "Music Box"), (11, "Vibraphone"),
    (13, "Xylophone"), (16, "Drawbar Organ"), (19, "Church Organ"),
    (21, "Accordion"), (24, "Nylon Guitar"), (25, "Steel Guitar"),
    (40, "Violin"), (42, "Cello"), (46, "Orchestral Harp"),
    (48, "String Ensemble"), (56, "Trumpet"), (68, "Oboe"),
    (71, "Clarinet"), (73, "Flute"), (80, "Synth Lead"), (88, "Synth Pad"),
]


def _midi_seconds(path):
    """Base duration of a MIDI file in seconds, or 0.0 if unreadable."""
    try:
        return mido.MidiFile(path).length
    except Exception:
        return 0.0


class ScoremillJukebox:
    def __init__(self, src_dir, local_port=None, remote=None, library=None):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk

        self.src_dir = src_dir
        self.library = library    # a MIDI directory to browse, or None (scripts)
        self.grouped = []         # [(group, sub, title, path)]
        self._visible = []        # [(title, path)] after filters
        self.player = None
        self._player_key = None   # marks which target the live player serves
        self.playing_path = None

        self.root = tk.Tk()
        self.root.title("Scoremill Jukebox")
        self.root.geometry("560x780")
        self.root.configure(bg=BG)
        self.root.minsize(440, 680)

        self.mode = tk.StringVar(value="remote" if remote else "local")
        self.local_port = tk.StringVar(value=local_port or "Auto")
        self.remote_host = tk.StringVar(value=(remote[0] if remote else ""))
        self.remote_port = tk.StringVar(
            value=str(remote[1] if remote else DEFAULT_FORWARD_PORT))

        self.genre = tk.StringVar(value="All")
        self.sub = tk.StringVar(value="All")
        self.search = tk.StringVar()
        self.now_playing = tk.StringVar(value="Nothing playing")
        self.status = tk.StringVar(value="Rendering scores...")
        self.duration = tk.StringVar(value="")
        self.count = tk.StringVar(value="")
        self.tempo = tk.IntVar(value=100)
        self.volume = tk.IntVar(value=100)
        self.voice = tk.StringVar(value="Grand Piano")
        self.autoplay = tk.BooleanVar(value=False)
        self.loop = tk.BooleanVar(value=False)
        self._tempo_job = self._vol_job = None

        self._build_ui()
        self.search.trace_add("write", lambda *_: self._filter())
        self.root.after(50, lambda: self._render(force=False))

    # ── UI ───────────────────────────────────────────────────
    def _build_ui(self):
        tk, ttk = self.tk, self.ttk

        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=20, pady=(14, 0))
        tk.Label(top, text="Scoremill Jukebox", bg=BG, fg=FG,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        self.status_lbl = tk.Label(top, textvariable=self.status, bg=BG,
                                   fg=DIM, font=("Segoe UI", 9))
        self.status_lbl.pack(side="right", pady=(6, 0))

        # Output target
        trow = tk.Frame(self.root, bg=BG)
        trow.pack(fill="x", padx=20, pady=(12, 0))
        tk.Label(trow, text="Output", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).pack(anchor="w")
        radios = tk.Frame(trow, bg=BG)
        radios.pack(fill="x")
        for label, val in (("Local synth", "local"), ("Remote (network)", "remote")):
            tk.Radiobutton(
                radios, text=label, value=val, variable=self.mode,
                command=self._on_target, bg=BG, fg=FG, selectcolor=BG3,
                activebackground=BG, activeforeground=FG,
                font=("Segoe UI", 10)).pack(side="left", padx=(0, 12))

        self.local_frame = tk.Frame(self.root, bg=BG)
        self.local_combo = ttk.Combobox(
            self.local_frame, textvariable=self.local_port,
            values=["Auto"], state="readonly", width=28)
        self.local_combo.pack(side="left")
        self.local_combo.bind("<<ComboboxSelected>>", lambda _: self._invalidate())

        self.remote_frame = tk.Frame(self.root, bg=BG)
        tk.Label(self.remote_frame, text="Host", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).pack(side="left")
        e1 = tk.Entry(self.remote_frame, textvariable=self.remote_host, width=16,
                      bg=BG2, fg=FG, insertbackground=FG, relief="flat", bd=4)
        e1.pack(side="left", padx=(4, 10))
        tk.Label(self.remote_frame, text="Port", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).pack(side="left")
        e2 = tk.Entry(self.remote_frame, textvariable=self.remote_port, width=7,
                      bg=BG2, fg=FG, insertbackground=FG, relief="flat", bd=4)
        e2.pack(side="left", padx=(4, 0))
        for e in (e1, e2):
            e.bind("<FocusOut>", lambda _: self._invalidate())
            e.bind("<Return>", lambda _: self._invalidate())

        self.target_holder = tk.Frame(self.root, bg=BG)
        self.target_holder.pack(fill="x", padx=20, pady=(6, 0))
        self._on_target()

        # Playlists (folders of a --library; blank for scoremill scripts)
        grow = tk.Frame(self.root, bg=BG)
        grow.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(grow, text="Genre", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        tk.Label(grow, text="Category", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w", padx=(14, 0))
        self.genre_combo = ttk.Combobox(grow, textvariable=self.genre,
                                        values=["All"], state="readonly", width=16)
        self.genre_combo.grid(row=1, column=0, sticky="w")
        self.genre_combo.bind("<<ComboboxSelected>>", self._on_genre)
        self.sub_combo = ttk.Combobox(grow, textvariable=self.sub,
                                      values=["All"], state="readonly", width=22)
        self.sub_combo.grid(row=1, column=1, sticky="ew", padx=(14, 0))
        self.sub_combo.bind("<<ComboboxSelected>>", lambda _: self._filter())
        grow.columnconfigure(1, weight=1)

        # Search
        srow = tk.Frame(self.root, bg=BG)
        srow.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(srow, text="Search", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Entry(srow, textvariable=self.search, bg=BG2, fg=FG,
                 insertbackground=FG, font=("Segoe UI", 11), relief="flat",
                 bd=4).pack(fill="x")

        # Song list
        lf = tk.Frame(self.root, bg=BG3)
        lf.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        self.listbox = tk.Listbox(
            lf, bg=BG2, fg=FG, selectbackground=ACCENT, selectforeground="white",
            font=("Segoe UI", 11), relief="flat", bd=0, highlightthickness=0,
            activestyle="none", exportselection=False)
        sb = tk.Scrollbar(lf, orient="vertical", command=self.listbox.yview,
                          bg=BG2, troughcolor=BG2, bd=0)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        sb.pack(side="right", fill="y", pady=2, padx=(0, 2))
        self.listbox.bind("<Double-Button-1>", lambda _: self._play())
        self.listbox.bind("<Return>", lambda _: self._play())

        crow = tk.Frame(self.root, bg=BG)
        crow.pack(fill="x", padx=20, pady=(2, 0))
        tk.Label(crow, textvariable=self.count, bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).pack(side="left", padx=(2, 0))
        self.rerender_btn = tk.Button(
            crow, text="↻  Re-render", command=lambda: self._render(force=True),
            bg=BG3, fg=FG, activebackground=BG2, font=("Segoe UI", 9),
            relief="flat", padx=8, pady=1, cursor="hand2")
        self.rerender_btn.pack(side="right")

        # Now playing
        np = tk.Frame(self.root, bg=BG)
        np.pack(fill="x", padx=20, pady=(8, 0))
        tk.Label(np, text="♪", bg=BG, fg=GREEN,
                 font=("Segoe UI", 14)).pack(side="left")
        tk.Label(np, textvariable=self.now_playing, bg=BG, fg=GREEN,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=(6, 0))
        tk.Label(np, textvariable=self.duration, bg=BG, fg=DIM,
                 font=("Segoe UI", 10)).pack(side="right")

        # Transport buttons
        bf = tk.Frame(self.root, bg=BG)
        bf.pack(fill="x", padx=20, pady=(12, 0))
        self.play_btn = tk.Button(
            bf, text="▶  Play", command=self._play, bg=GREEN, fg="#1a1a2e",
            activebackground="#3dbb92", font=("Segoe UI", 12, "bold"),
            relief="flat", padx=24, pady=7, cursor="hand2")
        self.play_btn.pack(side="left")
        tk.Button(bf, text="■  Stop", command=self._stop, bg=RED, fg="white",
                  activebackground="#d03050", font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=24, pady=7, cursor="hand2").pack(
                      side="left", padx=(12, 0))
        self.auto_btn = tk.Button(
            bf, text="↻  Auto", command=self._toggle_auto, bg=BG3, fg=FG,
            activebackground=BG2, font=("Segoe UI", 11), relief="flat",
            padx=14, pady=7, cursor="hand2")
        self.auto_btn.pack(side="left", padx=(16, 0))
        self.loop_btn = tk.Button(
            bf, text="⟳  Loop", command=self._toggle_loop, bg=BG3, fg=FG,
            activebackground=BG2, font=("Segoe UI", 11), relief="flat",
            padx=14, pady=7, cursor="hand2")
        self.loop_btn.pack(side="left", padx=(8, 0))

        # Tempo
        tf = tk.Frame(self.root, bg=BG)
        tf.pack(fill="x", padx=20, pady=(12, 0))
        tk.Label(tf, text="Tempo", bg=BG, fg=DIM, font=("Segoe UI", 9)).pack(anchor="w")
        tr = tk.Frame(tf, bg=BG)
        tr.pack(fill="x")
        tk.Scale(tr, from_=50, to=200, orient="horizontal", variable=self.tempo,
                 command=self._on_tempo, bg=BG, fg=FG, troughcolor=BG2,
                 highlightthickness=0, sliderrelief="flat", showvalue=False,
                 sliderlength=20).pack(side="left", fill="x", expand=True)
        self.tempo_lbl = tk.Label(tr, text="100%", bg=BG, fg=FG,
                                  font=("Segoe UI", 11, "bold"), width=5)
        self.tempo_lbl.pack(side="left", padx=(6, 0))

        # Volume
        vf = tk.Frame(self.root, bg=BG)
        vf.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(vf, text="Volume", bg=BG, fg=DIM, font=("Segoe UI", 9)).pack(anchor="w")
        vr = tk.Frame(vf, bg=BG)
        vr.pack(fill="x")
        tk.Scale(vr, from_=0, to=127, orient="horizontal", variable=self.volume,
                 command=self._on_volume, bg=BG, fg=FG, troughcolor=BG2,
                 highlightthickness=0, sliderrelief="flat", showvalue=False,
                 sliderlength=20).pack(side="left", fill="x", expand=True)
        self.vol_lbl = tk.Label(vr, text="100", bg=BG, fg=FG,
                                font=("Segoe UI", 11, "bold"), width=4)
        self.vol_lbl.pack(side="left", padx=(6, 0))

        # Voice
        vcf = tk.Frame(self.root, bg=BG)
        vcf.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(vcf, text="Voice", bg=BG, fg=DIM, font=("Segoe UI", 9)).pack(anchor="w")
        vc = ttk.Combobox(vcf, textvariable=self.voice,
                          values=[n for _, n in VOICES], state="readonly", width=22)
        vc.pack(anchor="w")
        vc.bind("<<ComboboxSelected>>", self._on_voice)

        tk.Frame(self.root, bg=BG, height=14).pack(fill="x")
        self.root.bind("<Escape>", lambda _: self._stop())

    # ── target selection ─────────────────────────────────────
    def _on_target(self):
        self.local_frame.pack_forget()
        self.remote_frame.pack_forget()
        frame = self.local_frame if self.mode.get() == "local" else self.remote_frame
        frame.pack(in_=self.target_holder, anchor="w")
        if self.mode.get() == "local":
            self._refresh_local_ports()
        self._invalidate()

    def _refresh_local_ports(self):
        try:
            names = mido.get_output_names()
        except Exception:
            names = []
        self.local_combo.configure(values=["Auto"] + names)
        if self.local_port.get() not in (["Auto"] + names):
            self.local_port.set("Auto")

    def _invalidate(self):
        """Drop the live player so the next Play rebinds to the current
        target. A playing track is stopped first."""
        if self.player is not None:
            try:
                self.player.close()
            except Exception:
                pass
        self.player = None
        self._player_key = None

    def _target_key(self):
        if self.mode.get() == "local":
            return ("local", self.local_port.get())
        return ("remote", self.remote_host.get().strip(),
                self.remote_port.get().strip())

    def _ensure_player(self):
        """Return a Player bound to the current target, creating it on
        first use or after a target change. Returns None and sets the
        status on failure (no MIDI port, forwarder unreachable, ...)."""
        key = self._target_key()
        if self.player is not None and self._player_key == key:
            return self.player
        if self.player is not None:
            try:
                self.player.close()
            except Exception:
                pass
            self.player = None
        try:
            if self.mode.get() == "local":
                name = self.local_port.get()
                port = None if name in ("", "Auto") else name
                p = Player(port=port, on_finish=self._finish)
            else:
                host = self.remote_host.get().strip()
                if not host:
                    self.status.set("Remote: enter a host")
                    return None
                try:
                    rport = int(self.remote_port.get())
                except ValueError:
                    rport = DEFAULT_FORWARD_PORT
                p = Player(remote=(host, rport), on_finish=self._finish)
        except Exception as e:
            self.status.set(f"Output error: {e}")
            self.status_lbl.config(fg=RED)
            return None
        p.set_tempo(self.tempo.get())
        p.set_volume(self.volume.get())
        p.set_voice(self._voice_program())
        self.player = p
        self._player_key = key
        self.status.set(f"● {p.port_name}")
        self.status_lbl.config(fg=DIM)
        return p

    # ── rendering ────────────────────────────────────────────
    def _render(self, force):
        self.status.set("Scanning library..." if self.library
                        else "Rendering scores...")
        self.rerender_btn.config(state="disabled")

        def work():
            try:
                if self.library:
                    grouped = scan_library(self.library)
                else:
                    grouped = [("", "", t, p) for t, p
                               in build_tracks(self.src_dir, force=force)]
            except Exception as e:
                self.root.after(0, lambda: self.status.set(f"Load failed: {e}"))
                self.root.after(0, lambda: self.rerender_btn.config(state="normal"))
                return
            self.root.after(0, lambda: self._loaded(grouped))

        threading.Thread(target=work, daemon=True).start()

    def _loaded(self, grouped):
        self.grouped = grouped
        groups = sorted({g for g, _s, _t, _p in grouped if g})
        self.genre_combo.configure(values=["All"] + groups)
        self._update_subs()
        self.rerender_btn.config(state="normal")
        self._filter()
        if self.mode.get() == "local":
            self._refresh_local_ports()
        self.status.set(f"● {len(grouped)} tracks ready")

    # ── list + filter ────────────────────────────────────────
    def _on_genre(self, _e=None):
        self.sub.set("All")
        self._update_subs()
        self._filter()

    def _update_subs(self):
        genre = self.genre.get()
        subs = sorted({s for g, s, _t, _p in self.grouped
                       if s and (genre == "All" or g == genre)})
        self.sub_combo.configure(values=["All"] + subs)
        if self.sub.get() not in (["All"] + subs):
            self.sub.set("All")

    def _filter(self):
        genre, sub = self.genre.get(), self.sub.get()
        q = self.search.get().lower()
        self.listbox.delete(0, "end")
        self._visible = []
        for g, s, title, path in self.grouped:
            if genre != "All" and g != genre:
                continue
            if sub != "All" and s != sub:
                continue
            if q and q not in title.lower():
                continue
            self.listbox.insert("end", title)
            self._visible.append((title, path))
        self.count.set(f"{len(self._visible)} tracks")

    # ── transport ────────────────────────────────────────────
    def _play(self):
        sel = self.listbox.curselection()
        if not sel or not self._visible:
            return
        title, path = self._visible[sel[0]]
        p = self._ensure_player()
        if p is None:
            return
        self.playing_path = path
        p.play(path, title)
        self.now_playing.set(title)
        secs = _midi_seconds(path)
        self.duration.set(f"{int(secs // 60)}m {int(secs % 60)}s" if secs else "")
        self.status.set("● Playing")
        self.status_lbl.config(fg=GREEN)

    def _stop(self):
        if self.player is not None:
            self.player.stop()
        self.now_playing.set("Stopped")
        self.duration.set("")
        self.status.set("● Ready")
        self.status_lbl.config(fg=DIM)

    def _finish(self):
        """Player thread signals a natural end; hop to the tk thread."""
        self.root.after(0, self._advance)

    def _advance(self):
        if self.loop.get() and self.playing_path:
            self._play_path(self.playing_path)
            return
        if self.autoplay.get():
            for i, (_, path) in enumerate(self._visible):
                if path == self.playing_path and i + 1 < len(self._visible):
                    self.listbox.selection_clear(0, "end")
                    self.listbox.selection_set(i + 1)
                    self.listbox.see(i + 1)
                    self._play()
                    return
        self.now_playing.set("Finished")
        self.duration.set("")
        self.status.set("● Ready")
        self.status_lbl.config(fg=DIM)

    def _play_path(self, path):
        p = self._ensure_player()
        if p is None:
            return
        title = next((t for t, pp in self._visible if pp == path),
                     pretty_title(path))
        self.playing_path = path
        p.play(path, title)
        self.now_playing.set(title)

    def _toggle_auto(self):
        self.autoplay.set(not self.autoplay.get())
        on = self.autoplay.get()
        self.auto_btn.config(bg=YELLOW if on else BG3, fg="#1a1a2e" if on else FG)

    def _toggle_loop(self):
        self.loop.set(not self.loop.get())
        on = self.loop.get()
        self.loop_btn.config(bg=GREEN if on else BG3, fg="#1a1a2e" if on else FG)

    def _on_tempo(self, val):
        v = int(float(val))
        self.tempo_lbl.config(text=f"{v}%")
        if self._tempo_job:
            self.root.after_cancel(self._tempo_job)
        self._tempo_job = self.root.after(
            60, lambda: self.player and self.player.set_tempo(v))

    def _on_volume(self, val):
        v = int(float(val))
        self.vol_lbl.config(text=str(v))
        if self._vol_job:
            self.root.after_cancel(self._vol_job)
        self._vol_job = self.root.after(
            60, lambda: self.player and self.player.set_volume(v))

    def _voice_program(self):
        name = self.voice.get()
        return next((prog for prog, n in VOICES if n == name), 0)

    def _on_voice(self, _e=None):
        if self.player:
            self.player.set_voice(self._voice_program())

    # ── lifecycle ────────────────────────────────────────────
    def _on_close(self):
        if self.player is not None:
            try:
                self.player.close()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()


def launch(src_dir, local_port=None, remote=None, library=None):
    """Open the jukebox GUI. With `library` set, browse that directory of
    existing MIDI files (subfolders as named playlists); otherwise render
    and play the scoremill scripts in `src_dir`."""
    ScoremillJukebox(src_dir, local_port=local_port, remote=remote,
                     library=library).run()


def main(argv):
    src_dir = DEFAULT_DIR
    port = None
    remote = None
    library = None
    bind = ("0.0.0.0", DEFAULT_FORWARD_PORT)
    mode = "gui"
    track_n = None
    i = 0
    try:
        while i < len(argv):
            a = argv[i]
            if a == "--dir":
                i += 1
                src_dir = argv[i]
            elif a == "--library":
                i += 1
                library = argv[i]
            elif a == "--port":
                i += 1
                port = argv[i]
            elif a == "--remote":
                i += 1
                remote = _parse_hostport(argv[i], DEFAULT_FORWARD_PORT)
            elif a == "--bind":
                i += 1
                bind = _parse_hostport(argv[i], DEFAULT_FORWARD_PORT)
            elif a == "--forward":
                mode = "forward"
            elif a == "--list":
                mode = "list"
            elif a == "--all":
                mode = "all"
            elif a == "--track":
                i += 1
                mode, track_n = "track", int(argv[i])
            else:
                print(f"unknown argument {a!r}", file=sys.stderr)
                return 2
            i += 1
    except (IndexError, ValueError):
        print(f"bad or missing value after {a!r} — usage: jukebox.py "
              f"[--dir D | --library D] [--port NAME] "
              f"[--remote HOST[:PORT]] [--bind HOST[:PORT]] "
              f"[--forward | --list | --track N | --all]", file=sys.stderr)
        return 2

    if mode == "forward":
        run_forwarder(bind[0], bind[1], piano_port=port)
        return 0

    source = library if library else src_dir
    if not os.path.isdir(source):
        print(f"no such directory: {source}", file=sys.stderr)
        return 2

    if mode == "gui":
        launch(src_dir, local_port=port, remote=remote, library=library)
        return 0

    tracks = ([(t, p) for (_g, _s, t, p) in scan_library(library)] if library
              else build_tracks(src_dir))
    if not tracks:
        print(f"no tracks in {source}", file=sys.stderr)
        return 1

    if mode == "list":
        for n, (title, path) in enumerate(tracks, 1):
            print(f"{n:2d}. {title}   ({os.path.basename(path)})")
        return 0

    if mode in ("track", "all"):
        done = threading.Event()
        order = ([track_n - 1] if mode == "track"
                 else list(range(len(tracks))))
        state = {"k": 0}

        def advance():
            state["k"] += 1
            if state["k"] < len(order):
                idx = order[state["k"]]
                title, path = tracks[idx]
                print(f"> {title}")
                player.play(path, title)
            else:
                done.set()

        try:
            player = Player(port=port, on_finish=advance, remote=remote)
        except (OSError, RuntimeError) as e:
            if remote:
                print(f"could not reach forwarder at "
                      f"{remote[0]}:{remote[1]} ({e}); is "
                      f"'jukebox.py --forward' running there?",
                      file=sys.stderr)
            else:
                print(e, file=sys.stderr)
            return 1
        if not 0 <= order[0] < len(tracks):
            print(f"track out of range (1-{len(tracks)})", file=sys.stderr)
            return 2
        title, path = tracks[order[0]]
        print(f"port: {player.port_name}")
        print(f"> {title}")
        player.play(path, title)
        try:
            while not done.wait(0.2):
                pass
        except KeyboardInterrupt:
            print("\n(interrupted)")
        finally:
            player.close()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
