#!/usr/bin/env python3
"""scoremill jukebox — play a folder of scoremill scores on a MIDI output.

A self-contained player for the example scores (or any directory of
scoremill scripts). It renders each script to MIDI once, then streams
the results to a MIDI output with live tempo, volume, and voice
control and a clean stop. No network, no server, no external library:
the playlist is whatever scoremill scripts you point it at.

  python jukebox.py                 # interactive, plays examples/
  python jukebox.py --list          # print the playlist and exit
  python jukebox.py --track 3       # play one track to the end and exit
  python jukebox.py --all           # play the whole playlist in order
  python jukebox.py --dir myscores --port "FluidSynth"

Interactive commands: a number or `p N` plays; `s` stop, `n` next,
`b` back, `a` autoplay, `l` loop, `t N` tempo %, `v N` volume 0-127,
`x N` voice (GM program 0-127), `r` re-render, `?` help, `q` quit.

Rendering runs each script with the host Python; a scoremill script
writes its .mid next to itself when run, so a script that builds
several songs (player_piano_studies.py) contributes several tracks.
Requires mido, and python-rtmidi for real output ports.
"""
import glob
import os
import subprocess
import sys
import threading
import time

import mido

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "examples")

GM_VOICES = {
    0: "Grand Piano", 1: "Bright Piano", 4: "Electric Piano",
    6: "Harpsichord", 8: "Celesta", 10: "Music Box", 11: "Vibraphone",
    19: "Church Organ", 24: "Nylon Guitar", 46: "Harp",
    48: "Strings", 56: "Trumpet", 71: "Clarinet", 73: "Flute",
}


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
    and one script may write several files. A script is skipped when
    the directory already holds MIDI at least as new as it, so a
    repeat launch with nothing edited renders nothing; pass force=True
    to render regardless. Returns (midi_paths, errors)."""
    errors = []
    existing = glob.glob(os.path.join(src_dir, "*.mid"))
    newest = max((os.path.getmtime(m) for m in existing), default=-1.0)
    for script in sorted(glob.glob(os.path.join(src_dir, "*.py"))):
        if not force and newest >= os.path.getmtime(script):
            continue                    # a render newer than this script exists
        log(f"rendering {os.path.basename(script)} ...")
        try:
            subprocess.run([sys.executable, script],
                           cwd=src_dir, capture_output=True, text=True,
                           timeout=120, check=True)
        except (subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as e:
            errors.append(f"{os.path.basename(script)}: {e}")
    midis = sorted(glob.glob(os.path.join(src_dir, "*.mid")))
    return midis, errors


# ── playback engine ──────────────────────────────────────────
class Player:
    """Streams a MIDI file to an output port in a background thread,
    applying live tempo, channel volume, and a voice override, and
    releasing every note and pedal on stop or finish."""

    HINTS = ("piano", "keyboard", "digital", "synth", "fluid", "usb")

    def __init__(self, port=None, on_finish=None):
        names = mido.get_output_names()
        if not names:
            raise RuntimeError("no MIDI output ports available "
                               "(install python-rtmidi, or start a synth)")
        if port:
            match = next((n for n in names if port.lower() in n.lower()), None)
            if match is None:
                raise RuntimeError(f"no output matching {port!r}; "
                                   f"available: {names}")
        else:
            match = self._auto_select(names)
        self.port_name = match
        if "through" in match.lower():
            print(f"warning: playing to {match!r}, a MIDI loopback — no "
                  f"sound unless a synth or instrument is chained to it. "
                  f"Connect an instrument, or pass --port.", file=sys.stderr)
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


# ── interactive console ──────────────────────────────────────
class Jukebox:
    def __init__(self, tracks, port=None):
        self.tracks = tracks                      # [(title, path)]
        self.idx = -1
        self.autoplay = False
        self.loop = False
        self.player = Player(port=port, on_finish=self._advance)

    def _advance(self):
        if self.loop and self.idx >= 0:
            self.start(self.idx)
        elif self.autoplay and self.idx + 1 < len(self.tracks):
            self.start(self.idx + 1)
        else:
            print("\n(finished)")

    def start(self, i):
        if not 0 <= i < len(self.tracks):
            return
        self.idx = i
        title, path = self.tracks[i]
        print(f"\n♪  {title}")
        self.player.play(path, title)

    def print_list(self):
        for i, (title, _) in enumerate(self.tracks):
            mark = "▶" if i == self.idx else " "
            print(f"  {mark} {i + 1:2d}. {title}")

    HELP = ("commands: <n>/p<n> play  s stop  n next  b back  "
            "a autoplay  l loop\n"
            "          t<pct> tempo  v<0-127> volume  x<prog> voice  "
            "r re-render  ? list  q quit")

    def run(self):
        print(f"scoremill jukebox  |  port: {self.player.port_name}  |  "
              f"{len(self.tracks)} tracks")
        self.print_list()
        print(self.HELP)
        try:
            while True:
                try:
                    raw = input("jukebox> ").strip()
                except EOFError:
                    break
                if not raw:
                    continue
                cmd, arg = raw[0].lower(), raw[1:].strip()
                if raw.isdigit():
                    self.start(int(raw) - 1)
                elif cmd == "p" and arg.isdigit():
                    self.start(int(arg) - 1)
                elif cmd == "s":
                    self.player.stop()
                    print("(stopped)")
                elif cmd == "n":
                    self.start(self.idx + 1)
                elif cmd == "b":
                    self.start(self.idx - 1)
                elif cmd == "a":
                    self.autoplay = not self.autoplay
                    print(f"autoplay {'on' if self.autoplay else 'off'}")
                elif cmd == "l":
                    self.loop = not self.loop
                    print(f"loop {'on' if self.loop else 'off'}")
                elif cmd == "t" and arg:
                    self.player.set_tempo(arg)
                    print(f"tempo {self.player.tempo_pct}%")
                elif cmd == "v" and arg:
                    self.player.set_volume(arg)
                    print(f"volume {self.player.volume}")
                elif cmd == "x" and arg.isdigit():
                    self.player.set_voice(arg)
                    name = GM_VOICES.get(self.player.voice, "program "
                                         f"{self.player.voice}")
                    print(f"voice: {name}")
                elif cmd == "r":
                    return "rerender"
                elif cmd == "?":
                    self.print_list()
                    print(self.HELP)
                elif cmd == "q":
                    break
                else:
                    print(self.HELP)
        finally:
            self.player.close()
        return None


def build_tracks(src_dir, force=False):
    midis, errors = render_scores(
        src_dir, log=lambda s: print(s, file=sys.stderr), force=force)
    for e in errors:
        print(f"warning: {e}", file=sys.stderr)
    return [(pretty_title(m), m) for m in midis]


def main(argv):
    src_dir = DEFAULT_DIR
    port = None
    mode = "interactive"
    track_n = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dir":
            i += 1
            src_dir = argv[i]
        elif a == "--port":
            i += 1
            port = argv[i]
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

    if not os.path.isdir(src_dir):
        print(f"no such directory: {src_dir}", file=sys.stderr)
        return 2

    tracks = build_tracks(src_dir)
    if not tracks:
        print(f"no scores found in {src_dir}", file=sys.stderr)
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
                print(f"♪  {title}")
                player.play(path, title)
            else:
                done.set()

        player = Player(port=port, on_finish=advance)
        if not 0 <= order[0] < len(tracks):
            print(f"track out of range (1-{len(tracks)})", file=sys.stderr)
            return 2
        title, path = tracks[order[0]]
        print(f"port: {player.port_name}")
        print(f"♪  {title}")
        player.play(path, title)
        try:
            while not done.wait(0.2):
                pass
        except KeyboardInterrupt:
            print("\n(interrupted)")
        finally:
            player.close()
        return 0

    # interactive, with re-render loop
    while True:
        jb = Jukebox(tracks, port=port)
        result = jb.run()
        if result == "rerender":
            tracks = build_tracks(src_dir, force=True)
            continue
        break
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
