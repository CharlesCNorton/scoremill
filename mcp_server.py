#!/usr/bin/env python3
"""scoremill MCP server.

Exposes scoremill to an MCP client (Claude Desktop, Claude Code, ...):
build a song from a JSON spec and get its MIDI, report, lint, chord
analysis, or engraved LilyPond, plus the motif transforms and the
chord/scale query helpers.

Register with Claude Code:

    claude mcp add --scope user scoremill -- \\
        python /path/to/scoremill/mcp_server.py

Requires `pip install "mcp[cli]" scoremill` (or run from a clone).

SONG SPEC (the shape every build tool takes)

    {
      "title": "Evening", "composer": "An Agent",
      "tempo": 96, "time": "4/4", "key": "Am", "pickup": 0,
      "humanize": 1, "swing": 0.5, "swing_unit": "eighth",
      "expressive": true, "fermata": 1.55, "trill_rate": 0.125,
      "dynamics": {"p": 45},
      "sections": [
        {"name": "A", "key": "Am", "time": "6/8",
         "time_changes": [{"bar": 9, "time": "9/8"}],
         "pedal": "bar", "soft": false,
         "rubato": {"depth": 0.05, "phrase": 2, "shape": "arch"},
         "swing": {"amount": 0.62, "unit": "eighth"},
         "voices": [
           {"name": "rh", "vel": 52, "octave": 4, "absolute": false,
            "bars": "!mf a4e c5e e5q. | ..."},
           {"name": "lh", "vel": 40, "channel": 0,
            "harmony": {"symbols": "Am G Am E7", "style": "broken",
                        "voicing": "smooth", "avoid": "rh"}},
           {"name": "arp", "harmony": {"symbols": "Am*2 E7*2",
                                       "slots": "half", "octave": 2,
                                       "pattern": "0 2 3 4 3 2",
                                       "unit": 0.3333333333333333}},
           {"name": "kit", "drums": true, "bars": "bde hh sn hh ... |"}
         ]}
      ],
      "tempo_changes": [{"section": "A", "bar": 5, "bpm": 80}],
      "ritardando": [{"section": "A", "from": 7, "to": 8, "bpm": 60}],
      "arrange": "A A"
    }
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:                                   # mcp 2
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:                    # mcp 1
    from mcp.server.fastmcp import FastMCP

import scoremill
from scoremill import (CompositionError, Song, chord_pitches, double,
                       harmonize, invert, rebar, retro, scale_pitches, shift,
                       stretch, transpose, transpose_chords)

mcp = FastMCP("scoremill")


def build_song(spec: dict) -> Song:
    """Construct a Song from a JSON spec (see the module docstring)."""
    s = Song(tempo=spec.get("tempo", 100), time=spec.get("time", "4/4"),
             key=spec.get("key", "C"), pickup=spec.get("pickup", 0.0),
             humanize=spec.get("humanize", 0), swing=spec.get("swing", 0.5),
             swing_unit=spec.get("swing_unit", "eighth"),
             expressive=spec.get("expressive", True),
             fermata=spec.get("fermata", 1.55),
             trill_rate=spec.get("trill_rate", 0.125),
             pitch_range=tuple(spec.get("pitch_range", (21, 108))),
             title=spec.get("title"), composer=spec.get("composer"),
             dynamics=spec.get("dynamics"))
    for sd in spec.get("sections", []):
        sec = s.section(sd["name"], key=sd.get("key"), time=sd.get("time"))
        for tc in sd.get("time_changes", []):
            sec.time_change(tc["bar"], tc["time"])
        for vd in sd.get("voices", []):
            if vd.get("drums"):
                v = sec.drums(vd.get("name", "kit"), vel=vd.get("vel", 70))
                v.absolute_onsets(vd.get("absolute", False))
            else:
                v = sec.voice(vd.get("name", "v"), vel=vd.get("vel", 50),
                              octave=vd.get("octave", 4),
                              program=vd.get("program", 0),
                              channel=vd.get("channel", 0),
                              absolute=vd.get("absolute", False))
            if vd.get("bars"):
                v.bars(vd["bars"])
            h = vd.get("harmony")
            if h:
                avoid = None
                if h.get("avoid"):
                    avoid = next((x for x in sec.voices
                                  if x.name.endswith("." + h["avoid"])), None)
                v.harmony(h["symbols"], style=h.get("style", "block"),
                          slots=h.get("slots", "bar"),
                          octave=h.get("octave", 3),
                          voicing=h.get("voicing", "plain"), avoid=avoid,
                          pattern=h.get("pattern"), unit=h.get("unit", 0.5))
        if sd.get("pedal") is not None:
            sec.pedal(sd["pedal"])
        if sd.get("soft"):
            sec.soft()
        if sd.get("rubato"):
            r = sd["rubato"]
            sec.rubato(r.get("depth", 0.05), r.get("phrase", 2),
                       r.get("shape", "arch"))
        if sd.get("swing"):
            sw = sd["swing"]
            sec.swing(sw.get("amount", 0.62), sw.get("unit", "eighth"))
    for tc in spec.get("tempo_changes", []):
        s.tempo_change(tc["section"], tc["bar"], tc["bpm"])
    for r in spec.get("ritardando", []):
        s.ritardando(r["section"], r["from"], r["to"], r["bpm"])
    if spec.get("arrange"):
        s.arrange(spec["arrange"])
    return s


def _guard(fn):
    """Wrap a tool so a CompositionError comes back as data, not a crash."""
    try:
        return fn()
    except CompositionError as e:
        return {"error": str(e)}


@mcp.tool()
def report(spec: dict) -> dict:
    """Build the song from `spec` and return report(): sections, voices,
    ranges, density, tempo-integrated duration, per-voice pitch metrics
    (pitch-class histogram, out-of-key rate, interval distribution,
    self-similarity, grace count), and lint findings."""
    return _guard(lambda: build_song(spec).report())


@mcp.tool()
def lint(spec: dict, mode: str = "full", only: str = "") -> dict:
    """Build the song and return its counterpoint findings. mode is
    "full" (collisions + parallels), "homophonic" (collisions only), or
    "strict" (adds voice crossings, unresolved leading tones, unprepared
    dissonances, tessitura warnings, and chords too wide for one hand).
    `only` names one section to check alone."""
    return _guard(lambda: {"findings": build_song(spec).lint(
        quiet=True, mode=mode, only=only or None)})


@mcp.tool()
def save_midi(spec: dict, path: str) -> dict:
    """Build the song and write it to a Standard MIDI File at `path`.
    Returns the path and the report."""
    def go():
        s = build_song(spec)
        s.save(path)
        return {"path": path, "report": s.report()}
    return _guard(go)


@mcp.tool()
def lilypond(spec: dict, path: str = "") -> dict:
    """Build the song and return engraved LilyPond source; also write it
    to `path` when given. Run the result through `lilypond` for a PDF."""
    return _guard(lambda: {"lilypond":
                           build_song(spec).to_lilypond(path or None)})


@mcp.tool()
def events(spec: dict) -> dict:
    """Build the song and return the raw event stream as a list of
    [tick, kind, channel, a, b] rows at 480 ticks per beat, kind in
    on/off/cc64/cc67/tempo."""
    return _guard(lambda: {"events": [list(e) for e in build_song(spec).events()]})


@mcp.tool()
def harmony_analysis(spec: dict, per: str = "beat") -> dict:
    """Build the song and name the chord that sounds in each window of a
    beat, half bar, or bar (`per`), merging runs of one chord: a list of
    {section, at, beats, chord}. Use it to check written harmony against
    the intended progression."""
    return _guard(lambda: {"chords": build_song(spec).chords(per=per)})


@mcp.tool()
def transform(kind: str, fragment: str, degrees: int = 0,
              axis: str = "g4", factor: float = 2.0,
              beats_per_bar: float = 4.0, semitones: int = 0,
              key: str = "C") -> dict:
    """Apply a motif transform to a notation fragment, string to string.
    kind: "shift" (uses degrees), "invert" (uses axis), "retro",
    "stretch" (uses factor), "rebar" (uses beats_per_bar), "transpose"
    (chromatic, uses semitones and the key the fragment is read in),
    "double" (adds each note a diatonic interval away: degrees 7 or -7
    for octaves, -2 for thirds), or "transpose_chords" (the fragment is
    chord symbols, moved by semitones and spelled for key, or for the
    new key when key is left at "C")."""
    def go():
        if kind == "transpose":
            return {"result": transpose(fragment, semitones, key)}
        if kind == "double":
            return {"result": double(fragment, degrees)}
        if kind == "transpose_chords":
            return {"result": transpose_chords(fragment, semitones,
                                               None if key == "C" else key)}
        if kind == "shift":
            return {"result": shift(fragment, degrees)}
        if kind == "invert":
            return {"result": invert(fragment, axis)}
        if kind == "retro":
            return {"result": retro(fragment)}
        if kind == "stretch":
            return {"result": stretch(fragment, factor)}
        if kind == "rebar":
            return {"result": rebar(fragment, beats_per_bar)}
        return {"error": f"unknown transform '{kind}'"}
    return _guard(go)


@mcp.tool()
def harmonize_melody(fragment: str, symbols: str, key: str = "C",
                     voices: int = 3, bass: str = "",
                     slots: str = "bar") -> dict:
    """Voice a melody fragment as chords under chord symbols (one per
    bar, or per `slots` beats given as a number), string to string, with
    the added notes chosen so that no voices, and none against the
    optional `bass` fragment, move in consecutive fifths or octaves."""
    return _guard(lambda: {"result": harmonize(
        fragment, symbols, key, voices, bass=bass or None, slots=slots)})


@mcp.tool()
def chords(symbol: str, octave: int = 4) -> dict:
    """The MIDI pitches of a chord symbol (Cmaj9, D7b9, F/A), slash bass
    first when present."""
    return _guard(lambda: {"pitches": chord_pitches(symbol, octave)})


@mcp.tool()
def scale(key: str, octave: int = 4) -> dict:
    """The seven MIDI pitches of a key's diatonic scale, ascending from
    the tonic (major keys give major, minor keys give natural minor)."""
    return _guard(lambda: {"pitches": scale_pitches(key, octave)})


@mcp.tool()
def cheatsheet() -> str:
    """The scoremill notation cheat sheet."""
    return scoremill.CHEATSHEET


if __name__ == "__main__":
    mcp.run()
