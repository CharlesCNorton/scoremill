#!/usr/bin/env python3
"""scoremill — text-notation MIDI composition for language-model agents.

Translates a compact text notation into expressive MIDI for solo piano
or multi-channel instruments. Input is validated at parse time — bar
lengths, instrument range, and voice alignment — and errors include
corrective suggestions.

Command line: --guide (worked example), --cheatsheet (syntax summary),
--test (test suite).

NOTATION REFERENCE

  Pitch     c d e f g a b, optional accidental (# b n), optional octave
            digit. The octave persists per voice until changed:
            "c4 d e f" = C4 D4 E4 F4. Octave 4 contains middle C. The
            song key signature is applied automatically: with key="F",
            "b" denotes B-flat and "bn" B natural. Minor keys ("Am",
            "Dm", ...) use the relative major signature; accidentals
            such as the raised leading tone are written explicitly.
            Pitches outside the instrument range (default 21-108, a
            standard piano) are rejected; Song(pitch_range=(lo, hi))
            overrides.
  Duration  trailing letter w h q e s t (whole through thirty-second),
            optional dot. Persists until changed: "c4q d e f gh" is
            three further quarters, then a half. "r" denotes a rest.
  Chord     [c4 e g]h — simultaneous pitches with a shared duration.
  Tuplet    {c4 d4 e4}q — members divide the span equally. Members may
            be chords ({[c4 e4] d4 [c4 e4]}q) and do not carry
            duration letters.
  Grace     +d5 — sounds approximately 60 ticks before the next note;
            multiple grace notes stack.
  Tie       trailing ~ joins the note to the next note, which must
            repeat the same pitch (validated). A tie on a voice's
            final note means laissez vibrer: the note rings past its
            written length.
  Marks     > accent, ' staccato, _ legato, ^ fermata (extends sounding
            length by Song(fermata=), written time unchanged), & rolled
            chord, % trill (diatonic upper neighbor at
            Song(trill_rate=) beats per alternation).
  Dynamics  !ppp !pp !p !mp !mf !f !ff !fff set the level until
            changed; "cresc" and "dim" interpolate toward the next
            dynamic mark, which must exist (validated).
  Barline   | asserts the bar is exactly full. Errors report the
            difference and the offending bar's tokens. Song(pickup=N)
            permits a short first bar of exactly N beats; a full first
            bar remains legal.

MOTIF TRANSFORMS (string to string)

  shift(frag, n)           diatonic transposition by n scale steps;
                           explicit alterations travel with their degree
  invert(frag, axis)       diatonic inversion about an axis pitch;
                           alterations are mirrored (# becomes b)
  retro(frag)              retrograde (fragment must not contain
                           barlines, dynamics, or ties)
  stretch(frag, factor)    augmentation (2) or diminution (0.5)
  rebar(frag, beats)       insert barlines every N beats, following
                           sticky durations; errors if a token would
                           cross a barline

HARMONY

  voice.harmony("C Am7 F G7", style=..., voicing=..., slots=...,
                avoid=...)
  Qualities: m 7 maj7 m7 6 m6 dim dim7 m7b5 aug sus2 sus4 9 maj9 m9
  add9 mmaj7 m11 7sus4 9sus4 7b5 7#5 7b9 7#9 11 13; slash bass (C/G);
  "." repeats the previous symbol. slots="half" places two symbols per
  bar. voicing="smooth" selects inversions that minimize movement from
  the previous chord. avoid=<voice> drops accompaniment chord tones
  that would double that voice's pitch classes on a shared onset and
  re-octaves figure tones that would collide at the unison. When the
  song has a pickup and the voice is empty, harmony inserts the pickup
  rest itself.
  Styles: block root fifth waltz alberti arp broken stride (waltz,
  stride, and broken fill fractional meters).

STRUCTURE

  s = Song(tempo=92, time="3/4", key="F", pickup=1)
  A = s.section("A")
  J = s.section("Jig", key="Bb", time="6/8")     # per-section overrides
  A.voice("rh", vel=52).bars("...")
  A.voice("str", program=48, channel=1)          # second timbre
  echo = A.variant("A2", vel_scale=0.85)
  s.arrange("A A2 Jig A")
  s.save("piece.mid"); s.play(); s.play(only="Jig", port="Synth")

EXPRESSION

  Song(swing=0.62, swing_unit="eighth"|"sixteenth", humanize=2,
       expressive=True, fermata=1.55, trill_rate=0.125)
  section.rubato(depth, phrase, shape="arch"|"surge")
  section.pedal("bar"|"half"|beats); section.soft()   # una corda
  s.tempo_change(section, bar, bpm)              # step change
  s.ritardando(section, bar_from, bar_to, bpm)   # linear ramp

ANALYSIS

  describe() prints a summary. lint() returns counterpoint findings
  located by bar and beat: unison collisions (including strikes
  against held notes) and consecutive parallel fifths and octaves on
  both the top and bottom lines of each voice pair.
  lint(mode="homophonic") keeps only collisions, for textures that
  double melody and accompaniment by design. report() returns a
  dictionary of sections, voices, ranges, density, duration (tempo
  map included), and lint results, suitable for assertions.

RAW ACCESS

  song.events() returns the fully expressive event stream as sorted
  (tick, kind, channel, a, b) tuples, kind in {"on", "off", "cc64",
  "cc67", "tempo"}, at TPB (480) ticks per beat. play(count_in=N)
  taps N beats before the music; play(progress=fn) calls fn(msg) per
  message. Notes may also be appended to a Voice directly; direct
  injection bypasses notation validation.

RECOMMENDED WORKFLOW

  1. Write sections with bars() and harmony(); structural errors are
     reported at parse time.
  2. Review describe(), lint(), and report().
  3. Audition with play(only=<section>).
  4. Render with save(<path>).
"""
import re
import sys
import time

import mido

TPB = 480
PIANO_LO, PIANO_HI = 21, 108

STEP = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
LETTERS = "cdefgab"
SHARP_ORDER = ["f", "c", "g", "d", "a", "e", "b"]
FLAT_ORDER = ["b", "e", "a", "d", "g", "c", "f"]
KEYS = {
    "C": (0, "#"), "G": (1, "#"), "D": (2, "#"), "A": (3, "#"),
    "E": (4, "#"), "B": (5, "#"), "F#": (6, "#"),
    "F": (1, "b"), "Bb": (2, "b"), "Eb": (3, "b"), "Ab": (4, "b"),
    "Db": (5, "b"), "Gb": (6, "b"),
}
RELATIVE_MAJOR = {
    "Am": "C", "Em": "G", "Bm": "D", "F#m": "A", "C#m": "E", "G#m": "B",
    "Dm": "F", "Gm": "Bb", "Cm": "Eb", "Fm": "Ab", "Bbm": "Db",
    "Ebm": "Gb",
}
DUR = {"w": 4.0, "h": 2.0, "q": 1.0, "e": 0.5, "s": 0.25, "t": 0.125}
DUR_ORDER = "whqest"
DYN = {"ppp": 18, "pp": 28, "p": 38, "mp": 48, "mf": 58, "f": 70,
       "ff": 84, "fff": 96}

CHORD_QUALITY = {
    "": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "dim": (0, 3, 6),
    "dim7": (0, 3, 6, 9), "m7b5": (0, 3, 6, 10),
    "sus4": (0, 5, 7), "sus2": (0, 2, 7), "aug": (0, 4, 8),
    "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9),
    "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14),
    "m9": (0, 3, 7, 10, 14), "add9": (0, 4, 7, 14),
    "mmaj7": (0, 3, 7, 11), "m11": (0, 3, 7, 10, 17),
    "7sus4": (0, 5, 7, 10), "9sus4": (0, 5, 7, 10, 14),
    "7b5": (0, 4, 6, 10), "7#5": (0, 4, 8, 10),
    "7b9": (0, 4, 7, 10, 13), "7#9": (0, 4, 7, 10, 15),
    "11": (0, 7, 10, 14, 17), "13": (0, 4, 10, 14, 21),
}

MARKS = "~>'_^&%"
NOTE_RE = re.compile(
    r"^([a-gr])(##|bb|#|b|n)?(\d)?([whqest]\.?)?([" + MARKS + r"]*)$")
CHORD_RE = re.compile(
    r"^\[([^\]]+)\]([whqest]\.?)?([" + MARKS + r"]*)$")
TUPLET_RE = re.compile(r"^\{([^}]+)\}([whqest]\.?)?$")
SYM_RE = re.compile(
    r"^([A-G])(#|b)?"
    r"(mmaj7|maj9|maj7|m7b5|dim7|add9|9sus4|7sus4|sus4|sus2"
    r"|m11|m9|m7|m6|7b9|7#9|7b5|7#5|aug|dim|m|13|11|9|7|6)?"
    r"(?:/([A-G])(#|b)?)?$")


class CompositionError(Exception):
    pass


def _resolve_key(key):
    """Accept major ('Eb') or minor ('Cm') names; return signature key."""
    if key in KEYS:
        return key
    if key in RELATIVE_MAJOR:
        return RELATIVE_MAJOR[key]
    raise CompositionError(
        f"unknown key '{key}' — majors {sorted(KEYS)} or minors "
        f"{sorted(RELATIVE_MAJOR)}")


# Chromatic tonic names for relabeling a transposed key. Flat spellings
# match scoremill's flat-key signatures; each supported key name maps to
# a pitch class here.
_KEY_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5,
           "F#": 6, "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
_PC_KEY = {0: "C", 1: "Db", 2: "D", 3: "Eb", 4: "E", 5: "F", 6: "F#",
           7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B"}


def _transpose_key(key, semitones):
    """Relabel a key name (major 'Eb' or minor 'Cm') by semitones,
    keeping the mode. Unknown names pass through unchanged."""
    minor = key.endswith("m")
    root = key[:-1] if minor else key
    if root not in _KEY_PC:
        return key
    name = _PC_KEY[(_KEY_PC[root] + semitones) % 12]
    return name + "m" if minor else name


def chord_pitches(symbol, octave=4):
    """The MIDI pitches of a chord symbol ('Cmaj9', 'D7b9', 'F/A'), with
    a slash bass first when present. A query helper for building
    accompaniment or checking harmony without a Song."""
    m = SYM_RE.match(symbol)
    if not m:
        raise CompositionError(
            f"chord_pitches: bad symbol '{symbol}' (qualities: "
            f"{' '.join(sorted(q for q in CHORD_QUALITY if q))})")
    root_l, root_a, qual, bass_l, bass_a = m.groups()
    root = 12 * (octave + 1) + _pc(root_l.lower(), root_a)
    tones = [root + iv for iv in CHORD_QUALITY[qual or ""]]
    if bass_l:
        tones.insert(0, 12 * octave + _pc(bass_l.lower(), bass_a))
    return tones


def scale_pitches(key, octave=4):
    """The seven MIDI pitches of a key's diatonic scale, ascending from
    the tonic. Major keys give the major scale; minor keys ('Am') give
    the natural minor. A query helper for melody construction."""
    sig = _resolve_key(key)
    tonic = key[0].lower()
    start = LETTERS.index(tonic)
    return [12 * (octave + 1) + _pc(LETTERS[(start + i) % 7], "", sig)
            + 12 * ((start + i) // 7) for i in range(7)]


def _pc(letter, acc, key="C"):
    v = STEP[letter]
    if acc == "n":
        return v
    if acc:
        return v + {"#": 1, "##": 2, "b": -1, "bb": -2}[acc]
    count, kind = KEYS.get(key, (0, "#"))
    if kind == "#" and letter in SHARP_ORDER[:count]:
        v += 1
    elif kind == "b" and letter in FLAT_ORDER[:count]:
        v -= 1
    return v


def _beats_name(x):
    """Return the duration-letter name for a beat value, if exact."""
    for sym, val in DUR.items():
        if abs(val - x) < 1e-9:
            return f"a '{sym}'"
        if abs(val * 1.5 - x) < 1e-9:
            return f"a dotted '{sym}.'"
    return None


# ════════════════════════ motif transforms ════════════════════════
def _tokenize(text):
    return re.findall(r"\{[^}]*\}\S*|\[[^\]]*\]\S*|\S+", text)


def _map_note_token(tok, fn, state):
    grace = tok.startswith("+")
    body = tok[1:] if grace else tok
    tm = TUPLET_RE.match(body)
    if tm:
        inner, dur = tm.group(1), tm.group(2) or ""
        parts = [_map_note_token(t, fn, state) for t in _tokenize(inner)]
        return ("+" if grace else "") + "{" + " ".join(parts) + "}" + dur
    m = CHORD_RE.match(body)
    if m:
        inner, dur, marks = m.group(1), m.group(2) or "", m.group(3) or ""
        parts = []
        for t in inner.split():
            nm = NOTE_RE.match(t)
            if not nm:
                raise CompositionError(f"transform: bad chord member '{t}'")
            parts.append(_apply(nm, fn, state, dur=""))
        return ("+" if grace else "") + "[" + " ".join(parts) + "]" + dur + marks
    nm = NOTE_RE.match(body)
    if not nm:
        return tok
    if nm.group(1) == "r":
        return tok
    return ("+" if grace else "") + _apply(nm, fn, state,
                                           dur=(nm.group(4) or ""))


def _apply(nm, fn, state, dur):
    letter, acc, octv = nm.group(1), nm.group(2), nm.group(3)
    if octv:
        state["oct"] = int(octv)
    nl, na, no = fn(letter, acc or "", state["oct"])
    marks = nm.group(5) or ""
    return f"{nl}{na}{no}{dur}{marks}"


def _transform(frag, fn):
    state = {"oct": 4}
    out = []
    for tok in _tokenize(frag):
        if tok == "|" or tok.startswith("!") or tok in ("cresc", "dim"):
            out.append(tok)
            continue
        out.append(_map_note_token(tok, fn, state))
    return " ".join(out)


def shift(frag, degrees):
    """Transpose every pitch in the fragment by N diatonic steps.
    Explicit alterations (#, b, n) travel with their scale degree."""
    def fn(letter, acc, octave):
        idx = octave * 7 + LETTERS.index(letter) + degrees
        return LETTERS[idx % 7], acc, idx // 7
    return _transform(frag, fn)


MIRROR_ACC = {"": "", "n": "n", "#": "b", "b": "#", "##": "bb", "bb": "##"}


def invert(frag, axis="g4"):
    """Invert the fragment diatonically about the given axis pitch.
    Alterations are mirrored: a raised degree inverts to a lowered one."""
    am = NOTE_RE.match(axis)
    if not am:
        raise CompositionError(f"invert: bad axis '{axis}'")
    a_idx = int(am.group(3) or 4) * 7 + LETTERS.index(am.group(1))
    def fn(letter, acc, octave):
        idx = octave * 7 + LETTERS.index(letter)
        idx = 2 * a_idx - idx
        return LETTERS[idx % 7], MIRROR_ACC[acc], idx // 7
    return _transform(frag, fn)


def retro(frag):
    """Reverse the fragment. Barlines, dynamics, and ties are not
    permitted inside; strip them and reapply around the result."""
    toks = _tokenize(frag)
    if "|" in toks:
        raise CompositionError("retro: remove barlines from the fragment")
    for t in toks:
        if t.startswith("!") or t in ("cresc", "dim"):
            raise CompositionError(
                "retro: remove dynamics from the fragment and reapply "
                "them around the result")
        if "~" in t:
            raise CompositionError(
                "retro: remove ties from the fragment — a reversed tie "
                "points the wrong way")
    state_dur = "q"
    explicit = []
    for t in toks:
        body = t[1:] if t.startswith("+") else t
        nm = NOTE_RE.match(body)
        cm = CHORD_RE.match(body)
        if nm:
            d = nm.group(4)
            if d:
                state_dur = d
                explicit.append(t)
            else:
                explicit.append(("+" if t.startswith("+") else "")
                                + body + state_dur)
        elif cm:
            d = cm.group(2)
            if d:
                state_dur = d
                explicit.append(t)
            else:
                explicit.append(t.replace("]", "]" + state_dur, 1))
        else:
            explicit.append(t)
    return " ".join(reversed(explicit))


def stretch(frag, factor):
    """Scale every duration by the factor: 2 (augmentation) or 0.5
    (diminution)."""
    if factor not in (2, 0.5):
        raise CompositionError("stretch: factor must be 2 or 0.5")
    shiftn = -1 if factor == 2 else 1

    def stretch_dur(d):
        if not d:
            return d
        i = DUR_ORDER.index(d[0]) + shiftn
        if not 0 <= i < len(DUR_ORDER):
            raise CompositionError(f"stretch: duration '{d}' out of range")
        return DUR_ORDER[i] + ("." if d.endswith(".") else "")

    out = []
    for tok in _tokenize(frag):
        if tok == "|" or tok.startswith("!") or tok in ("cresc", "dim"):
            out.append(tok)
            continue
        grace = tok.startswith("+")
        body = tok[1:] if grace else tok
        tm = TUPLET_RE.match(body)
        if tm:
            out.append(("+" if grace else "") + "{" + tm.group(1) + "}"
                       + stretch_dur(tm.group(2) or ""))
            continue
        cm = CHORD_RE.match(body)
        if cm:
            nd = stretch_dur(cm.group(2) or "")
            out.append(("+" if grace else "") + "[" + cm.group(1) + "]"
                       + nd + (cm.group(3) or ""))
            continue
        nm = NOTE_RE.match(body)
        if nm:
            nd = stretch_dur(nm.group(4) or "")
            out.append(("+" if grace else "")
                       + (nm.group(1) + (nm.group(2) or "")
                          + (nm.group(3) or "") + nd + (nm.group(5) or "")))
        else:
            out.append(tok)
    return " ".join(out)


def rebar(frag, beats_per_bar):
    """Insert barlines every `beats_per_bar` beats, honoring sticky
    durations, dots, tuplets, chords, graces, and dynamics tokens.
    Errors if a token would cross a barline or the fragment does not
    end on one."""
    toks = _tokenize(frag)
    if "|" in toks:
        raise CompositionError("rebar: fragment already contains barlines")

    def dur_of(durtok, state):
        if durtok:
            base = DUR[durtok[0]]
            state["dur"] = base * 1.5 if durtok.endswith(".") else base
        return state["dur"]

    state = {"dur": 1.0}
    out = []
    filled = 0.0
    for tok in toks:
        beats = 0.0
        body = tok[1:] if tok.startswith("+") else tok
        if tok.startswith("!") or tok in ("cresc", "dim"):
            pass
        elif tok.startswith("+"):
            pass                      # grace notes carry no time
        else:
            tm = TUPLET_RE.match(body)
            cm = CHORD_RE.match(body)
            nm = NOTE_RE.match(body)
            if tm:
                beats = dur_of(tm.group(2), state)
            elif cm:
                beats = dur_of(cm.group(2), state)
            elif nm:
                beats = dur_of(nm.group(4), state)
            else:
                raise CompositionError(f"rebar: unrecognized token '{tok}'")
        if beats - (beats_per_bar - filled) > 1e-9:
            raise CompositionError(
                f"rebar: token '{tok}' ({beats} beats) crosses a barline "
                f"with {beats_per_bar - filled} beats left in the bar — "
                f"split it or choose a different bar length")
        out.append(tok)
        filled += beats
        if abs(filled - beats_per_bar) < 1e-9:
            out.append("|")
            filled = 0.0
    if filled > 1e-9:
        raise CompositionError(
            f"rebar: fragment ends {beats_per_bar - filled} beats short "
            f"of a full bar")
    return " ".join(out)


# ════════════════════════ core model ════════════════════════
class Note:
    __slots__ = ("pitches", "beats", "vel", "gate", "tie", "grace",
                 "roll", "trill")
    def __init__(self, pitches, beats, vel, gate=0.92, tie=False,
                 grace=False, roll=False, trill=False):
        self.pitches = pitches
        self.beats = beats
        self.vel = vel
        self.gate = gate
        self.tie = tie
        self.grace = grace
        self.roll = roll
        self.trill = trill


def _suggest(raw):
    """Return a correction hint for an unrecognized token, if any."""
    hints = []
    if raw and raw[0] in MARKS:
        hints.append(f"marks go after the duration — try "
                     f"'{raw[1:]}{raw[0]}'")
    if raw != raw.lower():
        hints.append(f"pitches are lowercase — try '{raw.lower()}'")
    m = re.match(r"^(\d)([a-g])(.*)$", raw)
    if m:
        hints.append(f"octave goes after the letter — try "
                     f"'{m.group(2)}{m.group(1)}{m.group(3)}'")
    if re.match(r"^[a-g].*\d\d", raw):
        hints.append("only one octave digit allowed")
    return ("  hint: " + "; ".join(hints)) if hints else ""


class Voice:
    def __init__(self, name, song, vel=50, octave=4, key=None,
                 program=0, channel=0, bpb=None):
        self.name = name
        self.song = song
        self.key = _resolve_key(key or song.key)
        self.program = program
        self.channel = channel
        self.bpb = bpb or song.beats_per_bar
        self.notes = []
        self._oct = octave
        self._dur = 1.0
        self._vel = vel
        self._cresc_from = None
        self._started = False

    def bars(self, text):
        beats_in_bar = 0.0
        bar_no = 1
        first_bar = not self._started
        bar_tokens = []
        for raw in _tokenize(text):
            if raw == "|":
                want = self.bpb
                if (first_bar and self.song.pickup
                        and abs(beats_in_bar - self.song.pickup) <= 1e-6):
                    want = self.song.pickup
                if abs(beats_in_bar - want) > 1e-6:
                    diff = want - beats_in_bar
                    how = (f"short by {diff}" if diff > 0
                           else f"over by {-diff}")
                    name = _beats_name(abs(diff))
                    if name:
                        how += f" beats ({name})"
                    else:
                        how += " beats"
                    hint = (f" (a {self.song.pickup}-beat pickup bar is "
                            f"also legal here)"
                            if first_bar and self.song.pickup else "")
                    raise CompositionError(
                        f"voice '{self.name}' bar {bar_no}: has "
                        f"{beats_in_bar} beats, expected {want} — {how}."
                        f"{hint}\n    bar was: {' '.join(bar_tokens)}")
                bar_no += 1
                beats_in_bar = 0.0
                bar_tokens = []
                first_bar = False
                self._started = True
                continue
            bar_tokens.append(raw)
            if raw.startswith("!"):
                if raw[1:] not in DYN:
                    raise CompositionError(
                        f"unknown dynamic '{raw}' "
                        f"(use !ppp !pp !p !mp !mf !f !ff !fff)")
                self._apply_dynamic(DYN[raw[1:]])
                continue
            if raw in ("cresc", "dim"):
                self._cresc_from = (len(self.notes), self._vel)
                continue
            if raw.startswith("+"):
                m = NOTE_RE.match(raw[1:])
                if not m or m.group(1) == "r":
                    raise CompositionError(f"bad grace note '{raw}'")
                self.notes.append(Note([self._pitch(m)], 0.0,
                                       max(20, self._vel - 8), grace=True))
                continue
            beats_in_bar += self._token(raw)
        if beats_in_bar > 1e-6:
            raise CompositionError(
                f"voice '{self.name}': trailing partial bar "
                f"({beats_in_bar} beats) — end on a barline '|'")
        return self

    def _apply_dynamic(self, target):
        if self._cresc_from is not None:
            i0, v0 = self._cresc_from
            span = [n for n in self.notes[i0:] if n.pitches and not n.grace]
            for k, n in enumerate(span):
                n.vel = int(v0 + (target - v0) * (k + 1) / (len(span) or 1))
            self._cresc_from = None
        self._vel = target

    def _token(self, raw):
        tm = TUPLET_RE.match(raw)
        if tm:
            inner, durtok = tm.group(1), tm.group(2)
            members = _tokenize(inner)
            if not members:
                raise CompositionError(f"empty tuplet '{raw}'")
            span = self._beats(durtok)
            each = span / len(members)
            for t in members:
                cm = CHORD_RE.match(t)
                if cm:
                    if cm.group(2):
                        raise CompositionError(
                            f"tuplet member '{t}' must not carry a "
                            f"duration — the span divides equally")
                    pitches = []
                    for ct in cm.group(1).split():
                        cn = NOTE_RE.match(ct)
                        if not cn or cn.group(1) == "r":
                            raise CompositionError(
                                f"bad chord member '{ct}' in tuplet {raw}")
                        pitches.append(self._pitch(cn))
                    self.notes.append(Note(pitches, each, self._vel,
                                           gate=0.9,
                                           tie="~" in (cm.group(3) or "")))
                    continue
                nm = NOTE_RE.match(t)
                if not nm:
                    raise CompositionError(
                        f"bad tuplet member '{t}' in {raw} (no duration "
                        f"letters inside tuplets)")
                if nm.group(4):
                    raise CompositionError(
                        f"tuplet member '{t}' must not carry a duration — "
                        f"the span '{durtok or 'sticky'}' divides equally")
                if nm.group(1) == "r":
                    self.notes.append(Note([], each, 0))
                else:
                    self.notes.append(Note([self._pitch(nm)], each,
                                           self._vel,
                                           gate=0.9,
                                           tie="~" in (nm.group(5) or "")))
            return span
        m = CHORD_RE.match(raw)
        if m:
            inner, durtok, marks = m.groups()
            pitches = []
            for t in inner.split():
                nm = NOTE_RE.match(t)
                if not nm or nm.group(1) == "r":
                    raise CompositionError(f"bad chord member '{t}' in {raw}")
                pitches.append(self._pitch(nm))
            beats = self._beats(durtok)
            self._push(pitches, beats, marks or "")
            return beats
        m = NOTE_RE.match(raw)
        if not m:
            raise CompositionError(
                f"voice '{self.name}': unrecognized token '{raw}'."
                + _suggest(raw))
        letter = m.group(1)
        beats = self._beats(m.group(4))
        if letter == "r":
            self.notes.append(Note([], beats, 0))
        else:
            self._push([self._pitch(m)], beats, m.group(5) or "")
        return beats

    def _pitch(self, m):
        letter, acc, octv = m.group(1), m.group(2), m.group(3)
        if octv:
            self._oct = int(octv)
        p = 12 * (self._oct + 1) + _pc(letter, acc, self.key)
        if not self.song.pitch_lo <= p <= self.song.pitch_hi:
            raise CompositionError(
                f"voice '{self.name}': {letter}{acc or ''}{self._oct} "
                f"(MIDI {p}) is outside the instrument range "
                f"{self.song.pitch_lo}-{self.song.pitch_hi}")
        return p

    def _diatonic_upper(self, pitch):
        for cand in range(pitch + 1, pitch + 3):
            pc = cand % 12
            for letter in LETTERS:
                if _pc(letter, "", self.key) == pc:
                    return cand
        return pitch + 2

    def _beats(self, durtok):
        if durtok:
            base = DUR[durtok[0]]
            self._dur = base * 1.5 if durtok.endswith(".") else base
        return self._dur

    def _push(self, pitches, beats, marks):
        vel = self._vel + (12 if ">" in marks else 0)
        gate = 0.92
        if "'" in marks:
            gate = 0.45
        if "_" in marks:
            gate = 1.04
        if "^" in marks:
            gate = self.song.fermata
        if "%" in marks:
            if len(pitches) != 1:
                raise CompositionError("trill '%' works on single notes")
            main = pitches[0]
            upper = self._diatonic_upper(main)
            unit = self.song.trill_rate
            n32 = max(2, int(beats / unit))
            for i in range(n32 - 1):
                self.notes.append(Note([main if i % 2 == 0 else upper],
                                       unit, max(20, vel - 6), gate=0.9))
            rem = beats - (n32 - 1) * unit
            self.notes.append(Note([main], rem, vel, gate))
            return
        self.notes.append(Note(pitches, beats, min(127, vel), gate,
                               tie="~" in marks, roll="&" in marks))

    # ── harmony ──────────────────────────────────────────
    def harmony(self, symbols, style="block", slots="bar", octave=3,
                voicing="plain", avoid=None):
        """Render chord symbols as an accompaniment figure. `octave`
        places the chord roots and is independent of the octave the
        voice uses for melodic input. `avoid` names another Voice:
        chord tones that would double its pitch classes on a shared
        onset are dropped, and single figure tones that would collide
        at the exact unison move down an octave. When the song defines
        a pickup and this voice is still empty, the pickup rest is
        inserted automatically."""
        if self.song.pickup and not self.notes:
            self.notes.append(Note([], self.song.pickup, 0))
        avoid_map = None
        if avoid is not None:
            avoid_map = {}
            t = 0.0
            for n in avoid.notes:
                if n.grace:
                    continue
                if n.pitches:
                    avoid_map.setdefault(round(t, 6), set()).update(n.pitches)
                t += n.beats
        if voicing not in ("plain", "smooth", "shell", "rootless", "drop2"):
            raise CompositionError(
                "harmony: voicing is plain, smooth, shell, rootless, "
                f"or drop2 (got {voicing!r})")
        slot_beats = self.bpb if slots == "bar" else self.bpb / 2
        prev_sym = None
        prev_voicing = None
        t0 = self.total_beats()
        for sym in symbols.split():
            if sym == "|":
                continue
            if sym == ".":
                if prev_sym is None:
                    raise CompositionError("harmony: '.' with no prior chord")
                sym = prev_sym
            prev_sym = sym
            tones, has_bass = self._chord_pitches(sym, octave)
            if voicing in ("shell", "rootless", "drop2"):
                tones = self._voice_chord(tones, has_bass, voicing)
            elif voicing == "smooth" and prev_voicing:
                tones = [tones[0]] + self._lead(prev_voicing[1:], tones[1:])
            prev_voicing = tones
            self._figure(tones, style, slot_beats, t0, avoid_map)
            t0 += slot_beats
        return self

    def _emit(self, pitches, beats, vel, offset, t0, avoid_map, gate=0.92):
        """Append one accompaniment note at t0+offset, yielding to the
        avoided voice: chords drop tones that double its pitch classes;
        single tones dodge exact unisons by an octave."""
        sounding = avoid_map.get(round(t0 + offset, 6)) if avoid_map else None
        if sounding:
            if len(pitches) > 1:
                classes = {p % 12 for p in sounding}
                kept = [p for p in pitches if p % 12 not in classes]
                if kept:
                    pitches = kept
            else:
                p = pitches[0]
                if p in sounding:
                    moved = p - 12 if p - 12 >= self.song.pitch_lo else p + 12
                    if moved not in sounding:
                        pitches = [moved]
        self.notes.append(Note(pitches, beats, vel, gate))

    @staticmethod
    def _lead(prev_upper, upper):
        if not prev_upper or not upper:
            return upper
        center = sum(prev_upper) / len(prev_upper)
        out = []
        for t in upper:
            best = min((t + 12 * k for k in (-1, 0, 1)),
                       key=lambda x: abs(x - center))
            out.append(max(PIANO_LO, min(PIANO_HI, best)))
        return sorted(out)

    def _chord_pitches(self, sym, octave):
        m = SYM_RE.match(sym)
        if not m:
            raise CompositionError(
                f"harmony: bad chord symbol '{sym}' (qualities: "
                f"{' '.join(sorted(q for q in CHORD_QUALITY if q))})")
        root_l, root_a, qual, bass_l, bass_a = m.groups()
        root = 12 * (octave + 1) + _pc(root_l.lower(), root_a)
        tones = [root + iv for iv in CHORD_QUALITY[qual or ""]]
        has_bass = False
        if bass_l:
            tones.insert(0, 12 * octave + _pc(bass_l.lower(), bass_a))
            has_bass = True
        return tones, has_bass

    @staticmethod
    def _voice_chord(tones, has_bass, mode):
        """Re-voice a chord's tones. 'shell' keeps root, third, and
        seventh (or fifth if there is no seventh); 'rootless' drops the
        root for the accompaniment while a slash bass, if present, is
        kept; 'drop2' lowers the second voice from the top by an octave.
        A slash bass is never disturbed."""
        bass = [tones[0]] if has_bass else []
        core = tones[1:] if has_bass else list(tones)
        if not core:
            return tones
        root = core[0]
        if mode == "shell":
            third = next((t for t in core if (t - root) % 12 in (3, 4)), None)
            seventh = next((t for t in core if (t - root) % 12 in (10, 11)),
                           None)
            fifth = next((t for t in core if (t - root) % 12 in (6, 7, 8)),
                         None)
            sel = [root] + [x for x in (third, seventh or fifth)
                            if x is not None]
            core = sorted(set(sel))
        elif mode == "rootless":
            if len(core) >= 3:
                core = core[1:]                      # drop the root
        elif mode == "drop2":
            core = sorted(core)
            if len(core) >= 2:
                core[-2] -= 12
                core = sorted(core)
        return bass + core

    def _figure(self, tones, style, beats, t0=0.0, avoid_map=None):
        v = self._vel
        root, top = tones[0], tones[1:]
        if style == "block":
            self._emit(tones, beats, v, 0.0, t0, avoid_map)
        elif style == "root":
            self._emit([root], beats, v, 0.0, t0, avoid_map)
        elif style == "fifth":
            self._emit([root, root + 7], beats, v, 0.0, t0, avoid_map)
        elif style == "waltz":
            off = min(1.0, beats)
            self._emit([root], off, v, 0.0, t0, avoid_map)
            chord = top if len(top) >= 2 else [root + 4, root + 7]
            while beats - off > 1e-6:
                d = min(1.0, beats - off)
                self._emit(chord, d, max(20, v - 8), off, t0, avoid_map)
                off += d
        elif style == "alberti":
            third = tones[1] if len(tones) > 1 else root + 4
            fifth = tones[2] if len(tones) > 2 else root + 7
            seq = [root, fifth, third, fifth]
            for i in range(int(beats * 2)):
                self._emit([seq[i % 4]], 0.5, max(20, v - 6), i * 0.5,
                           t0, avoid_map)
        elif style == "arp":
            seq = tones + [root + 12]
            for i in range(int(beats * 2)):
                self._emit([seq[i % len(seq)]], 0.5, max(20, v - 6),
                           i * 0.5, t0, avoid_map)
        elif style == "stride":
            chord = [t + 12 for t in top] or [root + 16, root + 19]
            use_fifth = False
            b = 0.0
            while b < beats - 1e-6:
                bass = root - 12 + (7 if use_fifth else 0)
                use_fifth = not use_fifth
                d = min(1.0, beats - b)
                self._emit([bass], d, v + 4, b, t0, avoid_map)
                b += d
                if b < beats - 1e-6:
                    d = min(1.0, beats - b)
                    self._emit(chord, d, max(20, v - 10), b, t0, avoid_map,
                               gate=0.5)
                    b += d
        elif style == "broken":
            self._emit([root], min(1.0, beats), v, 0.0, t0, avoid_map)
            if beats > 1 + 1e-6:
                self._emit([root + 7], min(1.0, beats - 1.0),
                           max(20, v - 6), 1.0, t0, avoid_map)
            rest = beats - 2
            if rest > 1e-6:
                self._emit([t + 12 for t in top] or [root + 12], rest,
                           max(20, v - 6), 2.0, t0, avoid_map)
        else:
            raise CompositionError(
                f"harmony: unknown style '{style}' (block root fifth waltz "
                f"alberti arp broken stride)")

    def total_beats(self):
        return sum(n.beats for n in self.notes)


class Section:
    def __init__(self, name, song, key=None, time=None):
        self.name = name
        self.song = song
        self.key = key
        if time:
            num, den = time.split("/")
            self.bpb = float(num) * 4.0 / float(den)
        else:
            self.bpb = song.beats_per_bar
        self.voices = []
        self.pedal_mode = None
        self.soft_pedal = False
        self.rubato_depth = 0.0
        self.rubato_phrase = 2
        self.rubato_shape = "arch"

    def voice(self, name, vel=50, octave=4, program=0, channel=0):
        v = Voice(f"{self.name}.{name}", self.song, vel, octave,
                  key=self.key, program=program, channel=channel,
                  bpb=self.bpb)
        self.voices.append(v)
        return v

    def pedal(self, mode="bar"):
        """Sustain pedal, re-applied every bar ("bar"), half bar
        ("half"), or every N beats when given a number."""
        self.pedal_mode = mode
        return self

    def soft(self, on=True):
        """Una corda: hold the soft pedal (CC67) through the section."""
        self.soft_pedal = on
        return self

    def rubato(self, depth=0.05, phrase=2, shape="arch"):
        """Tempo inflection per phrase: "arch" presses forward through
        the phrase and relaxes its end; "cradle" broadens mid-phrase."""
        if shape not in ("arch", "cradle"):
            raise CompositionError('rubato: shape is "arch" or "cradle"')
        self.rubato_depth = depth
        self.rubato_phrase = phrase
        self.rubato_shape = shape
        return self

    def locate(self, t):
        """Render a section-relative beat offset as 'bar B beat N',
        accounting for an anacrusis when the song has a pickup and this
        section's voices begin with one."""
        bpb = self.bpb
        pu = self.song.pickup
        sec_len = max((v.total_beats() for v in self.voices), default=0.0)
        anac = (bool(pu) and round(sec_len % bpb, 6) != 0
                and round((sec_len - pu) % bpb, 6) == 0)
        if anac:
            if t < pu - 1e-9:
                return f"pickup beat {t + 1:g}"
            t -= pu
        bar = int(round(t, 6) // bpb) + 1
        beat = t - (bar - 1) * bpb + 1
        return f"bar {bar} beat {beat:g}"

    def variant(self, name, vel_scale=1.0):
        """Return a copy of this section with velocities scaled."""
        clone = self.song.section(name, key=self.key)
        clone.bpb = self.bpb
        clone.pedal_mode = self.pedal_mode
        clone.soft_pedal = self.soft_pedal
        clone.rubato_depth = self.rubato_depth
        clone.rubato_phrase = self.rubato_phrase
        clone.rubato_shape = self.rubato_shape
        for v in self.voices:
            nv = Voice(f"{name}.{v.name.split('.', 1)[1]}", self.song,
                       key=v.key, program=v.program, channel=v.channel,
                       bpb=v.bpb)
            for n in v.notes:
                nv.notes.append(Note(list(n.pitches), n.beats,
                                     max(15, min(127, int(n.vel * vel_scale))),
                                     n.gate, n.tie, n.grace, n.roll, n.trill))
            clone.voices.append(nv)
        return clone

    def length_beats(self):
        for v in self.voices:
            if v._cresc_from is not None:
                raise CompositionError(
                    f"voice '{v.name}': 'cresc'/'dim' never reaches a "
                    f"dynamic mark — follow it with one of !pp..!ff")
            body = [n for n in v.notes if not n.grace]
            for i, n in enumerate(body):
                if n.tie and n.pitches:
                    nxt = body[i + 1] if i + 1 < len(body) else None
                    if nxt is None:
                        continue          # laissez vibrer on the final note
                    if nxt.pitches != n.pitches:
                        raise CompositionError(
                            f"voice '{v.name}': tie on MIDI "
                            f"{n.pitches} is not followed by the same "
                            f"pitch — remove '~' or repeat the note")
        lens = {v.name: v.total_beats() for v in self.voices}
        vals = set(round(x, 4) for x in lens.values())
        if len(vals) > 1:
            pretty = {k: f"{x / self.bpb:.2f} bars" for k, x in lens.items()}
            raise CompositionError(
                f"section '{self.name}': voices differ in length: {pretty}")
        return next(iter(vals)) if vals else 0.0


class Song:
    def __init__(self, tempo=100, time="4/4", key="C", pickup=0.0,
                 humanize=0, swing=0.5, swing_unit="eighth",
                 expressive=True, fermata=1.55, trill_rate=0.125,
                 pitch_range=(PIANO_LO, PIANO_HI)):
        self.tempo = tempo
        num, den = time.split("/")
        self.beats_per_bar = float(num) * 4.0 / float(den)
        _resolve_key(key)          # validate early
        self.key = key
        self.pitch_lo, self.pitch_hi = pitch_range
        self.pickup = pickup
        self.humanize = humanize
        self.swing = swing
        if swing_unit not in ("eighth", "sixteenth"):
            raise CompositionError(
                'swing_unit is "eighth" or "sixteenth"')
        self.swing_unit = swing_unit
        self.expressive = expressive
        self.fermata = fermata
        self.trill_rate = trill_rate
        self.sections = {}
        self.order = []
        self._tempo_changes = {}
        self._ramps = []           # (section, bar_from, bar_to, bpm_to)

    def section(self, name, key=None, time=None):
        s = Section(name, self, key=key, time=time)
        self.sections[name] = s
        return s

    def arrange(self, order):
        self.order = order.split()
        for name in self.order:
            if name not in self.sections:
                raise CompositionError(f"arrange: unknown section '{name}'")
        return self

    def transpose(self, semitones):
        """Shift every already-entered note by a number of semitones,
        in place, and relabel the keys. Call it after the sections are
        written. Raises if any note would leave the instrument range."""
        for sec in self.sections.values():
            for v in sec.voices:
                for n in v.notes:
                    for p in n.pitches:
                        if not self.pitch_lo <= p + semitones <= self.pitch_hi:
                            raise CompositionError(
                                f"transpose by {semitones}: MIDI {p} would "
                                f"leave the range {self.pitch_lo}-"
                                f"{self.pitch_hi}")
                    n.pitches = [p + semitones for p in n.pitches]
            if sec.key:
                sec.key = _transpose_key(sec.key, semitones)
        self.key = _transpose_key(self.key, semitones)
        return self

    def tempo_change(self, section, bar, bpm):
        self._tempo_changes[(section, bar)] = bpm

    def ritardando(self, section, bar_from, bar_to, bpm_to):
        """Apply a linear tempo ramp across the given bars. A target
        faster than the prevailing tempo produces an accelerando."""
        self._ramps.append((section, bar_from, bar_to, bpm_to))

    # ── rendering ────────────────────────────────────────
    def _swing_shift(self, tick):
        if abs(self.swing - 0.5) < 1e-6:
            return 0
        period = TPB if self.swing_unit == "eighth" else TPB // 2
        if tick % period == period // 2:
            return int((self.swing - 0.5) * period)
        return 0

    def _base_bpm_fn(self, sec_name, sec):
        steps = sorted(((bar, bpm) for (sn, bar), bpm
                        in self._tempo_changes.items() if sn == sec_name))
        ramps = [(f, t, bpm) for (sn, f, t, bpm) in self._ramps
                 if sn == sec_name]

        def at(pos_ticks):
            bar = pos_ticks / (sec.bpb * TPB) + 1
            bpm = self.tempo
            for b, v in steps:
                if bar >= b:
                    bpm = v
            for f, t, v in ramps:
                if bar >= t:
                    bpm = v
                elif bar >= f:
                    frac = (bar - f) / max(1e-9, (t - f))
                    bpm = bpm + (v - bpm) * frac
            return bpm
        return at, bool(steps or ramps)

    def _events(self, order=None):
        import math
        import random
        rng = random.Random(20)
        events = []
        cursor = 0
        order = order or self.order or list(self.sections)
        for sec_name in order:
            sec = self.sections[sec_name]
            sec_len = sec.length_beats()
            bar_ticks = int(sec.bpb * TPB)
            for v in sec.voices:
                ch = v.channel
                sounding = [n for n in v.notes if n.pitches and not n.grace]
                avg = (sum(p for n in sounding for p in n.pitches)
                       / max(1, sum(len(n.pitches) for n in sounding)))
                t = cursor
                carried = None
                pending_grace = []
                for i, n in enumerate(v.notes):
                    if n.grace:
                        pending_grace.append(n)
                        continue
                    ticks = int(n.beats * TPB)
                    if n.pitches:
                        nxt = next((m for m in v.notes[i + 1:]
                                    if not m.grace), None)
                        if n.tie and nxt and nxt.pitches == n.pitches:
                            carried = carried if carried is not None else t
                        else:
                            start = carried if carried is not None else t
                            carried = None
                            length = t + ticks - start
                            start += self._swing_shift(start - cursor)
                            for gi, g in enumerate(reversed(pending_grace)):
                                gt = max(cursor, start - 60 * (gi + 1))
                                for p in g.pitches:
                                    events.append((gt, "on", ch, p, g.vel))
                                    events.append((gt + 55, "off", ch, p, 0))
                            pending_grace = []
                            vel = n.vel
                            if self.expressive:
                                if (start - cursor) % bar_ticks == 0:
                                    vel += 3
                                top = max(n.pitches)
                                vel += max(-6, min(6, int((top - avg) / 4)))
                            if self.humanize:
                                vel += rng.randint(-2, 2)
                            jitter = (rng.randint(-self.humanize,
                                                  self.humanize) * 4
                                      if self.humanize else 0)
                            on_t = max(0, start + jitter)
                            gate = n.gate
                            if n.tie and nxt is None:
                                gate = max(gate, self.fermata)   # l.v.
                            off_t = start + int(length * gate)
                            for pi, p in enumerate(sorted(n.pitches)):
                                pv = vel
                                if (self.expressive and len(n.pitches) > 1
                                        and p == max(n.pitches)):
                                    pv += 5
                                roll_off = (pi * 28 if n.roll else 0)
                                events.append((on_t + roll_off, "on", ch, p,
                                               max(1, min(127, pv))))
                                events.append((off_t, "off", ch, p, 0))
                    t += ticks
            if sec.pedal_mode:
                if isinstance(sec.pedal_mode, (int, float)):
                    step = max(1, int(sec.pedal_mode * TPB))
                else:
                    step = int(bar_ticks * (0.5 if sec.pedal_mode == "half"
                                            else 1))
                pos = cursor
                end = cursor + int(sec_len * TPB)
                chans = sorted({v.channel for v in sec.voices})
                while pos < end:
                    for ch in chans:
                        events.append((pos + 10, "cc64", ch, 127, 0))
                        events.append((pos + step - 20, "cc64", ch, 0, 0))
                    pos += step
            if sec.soft_pedal:
                for ch in sorted({v.channel for v in sec.voices}):
                    events.append((cursor + 5, "cc67", ch, 127, 0))
                    events.append((cursor + int(sec_len * TPB) - 10,
                                   "cc67", ch, 0, 0))
            bpm_at, has_plan = self._base_bpm_fn(sec_name, sec)
            total = int(sec_len * TPB)
            if sec.rubato_depth > 0:
                phrase_ticks = int(sec.rubato_phrase * bar_ticks)
                pos = 0
                while pos < total:
                    x = (pos % phrase_ticks) / phrase_ticks
                    bend = sec.rubato_depth * math.sin(math.pi * x)
                    mult = (1.0 + bend if sec.rubato_shape == "arch"
                            else 1.0 - bend)
                    if x > 0.85 and sec.rubato_shape == "arch":
                        mult *= 1.0 - sec.rubato_depth * 1.2
                    events.append((cursor + pos, "tempo", 0,
                                   bpm_at(pos) * mult, 0))
                    pos += TPB
            elif has_plan:
                pos = 0
                while pos < total:
                    events.append((cursor + pos, "tempo", 0, bpm_at(pos), 0))
                    pos += TPB
            cursor += int(sec_len * TPB)
        events.sort(key=lambda e: (e[0], e[1] != "off"))
        return events, cursor

    def _midifile(self, order=None):
        events, total = self._events(order)
        mid = mido.MidiFile(type=0, ticks_per_beat=TPB)
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage("set_tempo",
                                   tempo=mido.bpm2tempo(self.tempo)))
        programs = {}
        for sec in self.sections.values():
            for v in sec.voices:
                programs.setdefault(v.channel, v.program)
        for ch, prog in sorted(programs.items()):
            tr.append(mido.Message("program_change", channel=ch,
                                   program=prog, time=0))
        last = 0
        for tick, kind, ch, a, b in events:
            dt = tick - last
            last = tick
            if kind == "on":
                tr.append(mido.Message("note_on", channel=ch, note=a,
                                       velocity=b, time=dt))
            elif kind == "off":
                tr.append(mido.Message("note_off", channel=ch, note=a,
                                       velocity=0, time=dt))
            elif kind in ("cc64", "cc67"):
                tr.append(mido.Message("control_change", channel=ch,
                                       control=int(kind[2:]), value=a,
                                       time=dt))
            elif kind == "tempo":
                tr.append(mido.MetaMessage(
                    "set_tempo", tempo=mido.bpm2tempo(a), time=dt))
        tr.append(mido.MetaMessage("end_of_track",
                                   time=max(0, total - last)))
        return mid

    def events(self, order=None):
        """Return the fully expressive event stream: sorted
        (tick, kind, channel, a, b) tuples at TPB (480) ticks per
        beat, kind in {"on", "off", "cc64", "cc67", "tempo"} with bpm
        in `a` for tempo events. This is exactly what save() and
        play() render; use it to work below the notation."""
        return self._events(order)[0]

    def _count_in_taps(self, count_in, pitch=84, vel=26):
        """Metronome taps for play(): (seconds_from_start, message)."""
        beat = 60.0 / self.tempo
        taps = []
        for i in range(int(count_in)):
            taps.append((i * beat,
                         mido.Message("note_on", channel=0, note=pitch,
                                      velocity=vel)))
            taps.append((i * beat + 0.08,
                         mido.Message("note_off", channel=0, note=pitch,
                                      velocity=0)))
        return taps

    def save(self, path, only=None):
        """Write the song to a standard MIDI file and return the path."""
        self._midifile([only] if only else None).save(path)
        return path

    def play(self, port=None, only=None, count_in=0, progress=None):
        """Stream the song to a MIDI output in real time.

        `port` selects an output by case-insensitive substring of its
        mido port name; when omitted, the first output that is not a
        software through-port is used. `count_in` taps N beats on a
        soft high tick before the music. `progress`, if given, is
        called with each message as it is sent. Sends all-notes-off
        and releases the pedals on every used channel when playback
        ends or is interrupted (Ctrl-C is safe). Returns the name of
        the port used."""
        names = mido.get_output_names()
        if not names:
            raise CompositionError("no MIDI output ports available")
        if port:
            chosen = next((n for n in names
                           if port.lower() in n.lower()), None)
            if chosen is None:
                raise CompositionError(
                    f"no MIDI output matching {port!r}; "
                    f"available: {names}")
        else:
            chosen = next((n for n in names
                           if "through" not in n.lower()), names[0])
        mid = self._midifile([only] if only else None)
        channels = sorted({v.channel for sec in self.sections.values()
                           for v in sec.voices})
        with mido.open_output(chosen) as out:
            try:
                if count_in:
                    t0 = time.monotonic()
                    for at, msg in self._count_in_taps(count_in):
                        wait = at - (time.monotonic() - t0)
                        if wait > 0:
                            time.sleep(wait)
                        out.send(msg)
                    time.sleep(max(0.0, count_in * 60.0 / self.tempo
                                   - (time.monotonic() - t0)))
                for msg in mid.play():
                    out.send(msg)
                    if progress:
                        progress(msg)
            finally:
                for ch in channels:
                    out.send(mido.Message("control_change", channel=ch,
                                          control=123, value=0))
                    out.send(mido.Message("control_change", channel=ch,
                                          control=64, value=0))
                    out.send(mido.Message("control_change", channel=ch,
                                          control=67, value=0))
        return chosen

    # ── feedback for agents ──────────────────────────────
    def _duration_s(self):
        """Total seconds, integrating the tempo map (step changes,
        ritardando ramps, and rubato) rather than assuming base tempo."""
        events, total = self._events()
        changes = sorted((tk, bpm) for (tk, kind, _, bpm, _) in events
                         if kind == "tempo")
        secs = 0.0
        cur = self.tempo
        prev = 0
        for tk, bpm in changes:
            if tk > prev:
                secs += (tk - prev) / TPB * 60.0 / cur
                prev = tk
            cur = bpm
        if total > prev:
            secs += (total - prev) / TPB * 60.0 / cur
        return round(secs, 1)

    def lint(self, quiet=False, mode="full"):
        """Check counterpoint across each section's voices, locating
        each finding by bar and beat. Collisions catch two voices
        sounding the same pitch at once, whether struck together or
        struck against a held note. Parallel fifths and octaves are
        checked on both the top and the bottom line of each voice pair.
        mode="homophonic" reports only collisions, for textures that
        deliberately double melody and accompaniment. Returns a list of
        finding strings; prints them unless quiet=True."""
        if mode not in ("full", "homophonic"):
            raise CompositionError('lint: mode is "full" or "homophonic"')
        all_issues = []
        order = self.order or list(self.sections)
        seen = set()
        for sec_name in order:
            if sec_name in seen:
                continue
            seen.add(sec_name)
            sec = self.sections[sec_name]
            issues = []
            spans = []
            for v in sec.voices:
                t = 0.0
                iv = []
                onsets = {}
                for n in v.notes:
                    if n.grace:
                        continue
                    if n.pitches:
                        iv.append((round(t, 6), round(t + n.beats, 6),
                                   set(n.pitches)))
                        onsets[round(t, 6)] = tuple(n.pitches)
                    t += n.beats
                spans.append((v.name, iv, onsets))
            for i in range(len(spans)):
                for j in range(i + 1, len(spans)):
                    n1, iv1, on1 = spans[i]
                    n2, iv2, on2 = spans[j]
                    seen_coll = set()
                    for (s1, e1, p1) in iv1:
                        for (s2, e2, p2) in iv2:
                            lo = max(s1, s2)
                            if min(e1, e2) - lo <= 1e-6:
                                continue
                            shared = p1 & p2
                            if not shared:
                                continue
                            key = (round(lo, 6), frozenset(shared))
                            if key in seen_coll:
                                continue
                            seen_coll.add(key)
                            held = round(lo, 6) not in (
                                set(on1) & set(on2))
                            tag = "held-unison" if held else "unison"
                            pitches = ",".join(str(p) for p in sorted(shared))
                            issues.append(
                                f"{tag} {n1}/{n2} at {sec.locate(lo)} "
                                f"(MIDI {pitches})")
                    if mode == "homophonic":
                        continue
                    common = sorted(set(on1) & set(on2))
                    pairs = [(t, on1[t], on2[t]) for t in common]
                    seen_par = set()
                    for k in range(1, len(pairs)):
                        _, a0, b0 = pairs[k - 1]
                        t1, a1, b1 = pairs[k]
                        for pick in (max, min):
                            x0, y0, x1, y1 = (pick(a0), pick(b0),
                                              pick(a1), pick(b1))
                            iv0 = abs(x0 - y0) % 12
                            ivn = abs(x1 - y1) % 12
                            if (x0 != x1 and y0 != y1
                                    and iv0 == ivn and iv0 in (0, 7)):
                                kind = "octaves" if iv0 == 0 else "fifths"
                                hi, low = max(x1, y1), min(x1, y1)
                                dkey = (round(t1, 6), kind, hi, low)
                                if dkey in seen_par:
                                    continue
                                seen_par.add(dkey)
                                issues.append(
                                    f"parallel {kind} {n1}/{n2} at "
                                    f"{sec.locate(t1)} ({hi}/{low})")
            if issues and not quiet:
                print(f"[lint] section {sec_name}:")
                for line in issues:
                    print("  " + line)
            all_issues.extend(f"[{sec_name}] {i}" for i in issues)
        if not quiet:
            print(f"[lint] {len(all_issues)} finding(s)")
        return all_issues

    def report(self):
        """Return a structured summary of the song: sections, voices,
        ranges, note density, tempo-integrated duration, and lint
        findings."""
        order = self.order or list(self.sections)
        out = {"tempo": self.tempo, "key": self.key,
               "beats_per_bar": self.beats_per_bar,
               "swing": self.swing, "sections": [], "lint": []}
        for name in order:
            sec = self.sections[name]
            ln = sec.length_beats()
            voices = []
            for v in sec.voices:
                pitches = [p for n in v.notes for p in n.pitches]
                notes = sum(1 for n in v.notes if n.pitches and not n.grace)
                voices.append({
                    "name": v.name, "channel": v.channel,
                    "program": v.program, "notes": notes,
                    "range": ([min(pitches), max(pitches)]
                              if pitches else None),
                    "density_nps": round(
                        notes / max(0.001, ln / self.tempo * 60), 2),
                })
            out["sections"].append({
                "name": name, "bars": ln / sec.bpb, "key": sec.key,
                "pedal": sec.pedal_mode, "soft": sec.soft_pedal,
                "rubato": sec.rubato_depth, "voices": voices,
            })
        out["duration_s"] = self._duration_s()
        out["lint"] = self.lint(quiet=True)
        return out

    def describe(self):
        order = self.order or list(self.sections)
        feats = []
        if abs(self.swing - 0.5) > 1e-6:
            feats.append(f"swing={self.swing}")
        if self.humanize:
            feats.append(f"humanize={self.humanize}")
        if self.expressive:
            feats.append("expressive")
        print(f"Song: {self.tempo}bpm, {self.beats_per_bar}-beat bars, "
              f"key {self.key}" + (f"  [{', '.join(feats)}]" if feats else ""))
        for name in order:
            sec = self.sections[name]
            ln = sec.length_beats()
            extras = []
            if sec.key:
                extras.append(f"key={sec.key}")
            if sec.bpb != self.beats_per_bar:
                extras.append(f"{sec.bpb}-beat bars")
            if sec.pedal_mode:
                extras.append(f"pedal={sec.pedal_mode}")
            if sec.soft_pedal:
                extras.append("soft")
            if sec.rubato_depth:
                extras.append(f"rubato={sec.rubato_depth}")
            chans = {v.channel for v in sec.voices}
            if chans != {0}:
                extras.append(f"channels={sorted(chans)}")
            print(f"  [{name}] {ln / sec.bpb:.1f} bars, "
                  f"{len(sec.voices)} voices"
                  + (f" ({', '.join(extras)})" if extras else ""))
        print(f"  total ~ {self._duration_s():.0f}s")


# ════════════════════════ documentation ════════════════════════
GUIDE = '''
WORKED EXAMPLE

    from scoremill import Song, shift

    s = Song(tempo=96, time="4/4", key="Am", humanize=1)

    MOTIF = "a4e c5e e5q d5e c5e"          # three beats of material
    A = s.section("A")
    A.voice("rh", vel=52).bars(
        f"!mp {MOTIF} b4q | {shift(MOTIF, -1)} a4q |"
        "  e5q {d5 c5 b4}q a4h |"           # triplet on beat two
        "  [a3 c4 e4]w^& |")                # rolled final chord, fermata
    lh = A.voice("lh", vel=36)
    lh.harmony("Am G Am E7", style="broken", voicing="smooth",
               avoid=A.voices[0])           # dodge the melody's pitches
    A.pedal("bar")
    s.ritardando("A", 3, 4, 70)             # smooth final rit
    s.arrange("A")

    s.describe()                            # printed summary
    print(s.report()["duration_s"])         # tempo-integrated duration
    s.lint()                                # findings, by bar and beat
    s.play(count_in=4)                       # tap four, then perform

WORKFLOW: write bars() (validated at parse time); review describe(),
lint(), and report(); audition with play(only=...); iterate; publish
with save(). Bar errors state the beat difference and show the
offending bar. Below the notation, song.events() is the raw stream.
'''

CHEATSHEET = '''
PITCH  c..b [+ # b n] [+octave]   sticky octave; key sig applies
DUR    w h q e s t [+ .]          sticky;  r = rest (re = eighth rest)
CHORD  [c4 e g]h   TUPLET {c d e}q or {[c4 e4] d4}q   GRACE +d5   TIE c5h~
MARKS  > accent  ' stacc  _ legato  ^ fermata  & roll  % trill
DYN    !ppp !pp !p !mp !mf !f !ff !fff   cresc/dim toward next !dyn
BAR    | must be exactly full (pickup= allows short OR full first bar)
LV     a tie on a voice's final note lets it ring (laissez vibrer)
HARMONY voice.harmony("C Am7 F G7", style=block|root|fifth|waltz|
        alberti|arp|broken|stride, voicing=plain|smooth, slots=bar|half,
        avoid=<voice>)   qualities incl 9 11 13 m11 7b9 7#9 7sus4 mmaj7
TRANSFORMS shift(frag,n) invert(frag,axis) retro(frag) stretch(frag,2)
        rebar(frag, beats_per_bar)
SONG   Song(tempo,time,key,pickup,humanize,swing,swing_unit,
        expressive,fermata,trill_rate)
       .section(name,key=,time=) .arrange("A A B A") .events()
       .tempo_change(sec,bar,bpm) .ritardando(sec,from,to,bpm)
       .describe() .lint(mode=) .report() .play(port=,only=,count_in=,
        progress=) .save(path)
SECTION .voice(name,vel,octave,program,channel) .pedal("bar"|"half"|N)
        .soft() .rubato(depth,phrase,shape) .variant(name, vel_scale)
'''


def _test():
    # Motif transforms produce the expected note strings.
    assert shift("c4q e4e g4e", 1) == "d4q f4e a4e"
    assert shift("g#4q", -1) == "f#4q"          # alterations travel
    assert invert("c4q e4q", axis="c4") == "c4q a3q"
    assert invert("c#4q", axis="c4") == "cb4q"  # alterations mirror
    assert retro("c4q e4e g4e") == "g4e e4e c4q"
    assert stretch("c4q d4e", 2) == "c4h d4q"

    # retro rejects dynamics and ties rather than reversing them.
    for bad, word in [("!mf c4q d4q", "dynamics"), ("c4q~ c4q", "ties")]:
        try:
            retro(bad)
            raise AssertionError("retro check did not fire")
        except CompositionError as e:
            assert word in str(e)

    # A mark placed before the pitch draws a corrective hint.
    try:
        Song().section("M").voice("m").bars(">c4q d4q e4q f4q |")
        raise AssertionError("mark-position hint did not fire")
    except CompositionError as e:
        assert "after the duration" in str(e)

    # cresc without a target dynamic is rejected at validation.
    orphan = Song()
    orphan.section("O").voice("m").bars("cresc c4q d4q e4q f4q |")
    try:
        orphan.report()
        raise AssertionError("cresc check did not fire")
    except CompositionError as e:
        assert "cresc" in str(e)

    # A tie not followed by the same pitch is rejected at validation.
    dangling = Song()
    dangling.section("D").voice("m").bars("c4h~ d4h |")
    try:
        dangling.report()
        raise AssertionError("tie check did not fire")
    except CompositionError as e:
        assert "tie" in str(e)

    # A minor key applies its signature: in D minor, 'b' is B-flat.
    minor = Song(key="Dm").section("K").voice("m")
    minor.bars("b4q d5q a4q b4q |")
    assert 70 in minor.notes[0].pitches, minor.notes[0].pitches

    # A triplet divides one beat into three equal members.
    triplet = Song().section("T").voice("m")
    triplet.bars("{c4 d4 e4}q c4q c4h |")
    assert abs(triplet.total_beats() - 4.0) < 1e-9
    assert len(triplet.notes) == 5
    assert abs(triplet.notes[0].beats - 1 / 3) < 1e-9

    # A ninth chord voices five pitches.
    ninths = Song().section("N").voice("x")
    ninths.harmony("Cmaj9 Dm9 G9 Cadd9 C6", style="block")
    assert len(ninths.notes[0].pitches) == 5

    # A ritardando emits a descending tempo ramp.
    rit = Song(tempo=100)
    rit.section("R").voice("m").bars("c4w | c4w | c4w | c4w |")
    rit.ritardando("R", 2, 4, 60)
    rit.arrange("R")
    tempos = [a for (_, k, _, a, _) in rit._events()[0] if k == "tempo"]
    assert len(tempos) >= 8 and tempos[-1] < 75, tempos[-3:]

    # A short bar is rejected with the beat difference and the bar's tokens.
    try:
        Song().section("E").voice("m").bars("c4q d4q e4q |")
        raise AssertionError("bar check did not fire")
    except CompositionError as e:
        assert "short by 1.0" in str(e) and "'q'" in str(e), e
    # An uppercase pitch is rejected with a correction hint.
    try:
        Song().section("E2").voice("m").bars("C4q |")
        raise AssertionError("suggestion did not fire")
    except CompositionError as e:
        assert "lowercase" in str(e)

    # report() returns the duration and per-voice pitch range.
    rep = Song(tempo=120)
    rep.section("A").voice("m").bars("c4q e4q g4q c5q |")
    rep.arrange("A")
    r = rep.report()
    assert r["duration_s"] == 2.0
    assert r["sections"][0]["voices"][0]["range"] == [60, 72], r

    # lint() detects parallel fifths, located by bar, droppable in
    # homophonic mode.
    par = Song()
    par.section("X").voice("a").bars("c4q d4q e4q f4q |")
    par.sections["X"].voice("b").bars("g4q a4q b4q c5q |")
    par.arrange("X")
    findings = par.lint(quiet=True)
    assert any("parallel fifths" in f for f in findings), findings
    assert all("bar" in f for f in findings), findings
    assert par.lint(quiet=True, mode="homophonic") == []

    # lint() catches a strike against a held note (not onset-aligned).
    held = Song()
    held.section("H").voice("a").bars("c4w |")
    held.sections["H"].voice("b").bars("rh c4h |")
    held.arrange("H")
    hf = held.lint(quiet=True)
    assert any("bar 1 beat 3" in f for f in hf), hf

    # rebar inserts barlines and rejects a token that crosses one.
    assert rebar("c4q d4 e4 d4 c4 d4", 3) == "c4q d4 e4 | d4 c4 d4 |"
    try:
        rebar("c4h d4h", 3)
        raise AssertionError("rebar crossing check did not fire")
    except CompositionError as e:
        assert "crosses" in str(e)

    # A tuplet may contain chords.
    tc = Song().section("TC").voice("m")
    tc.bars("{[c4 e4] d4 [c4 e4]}q c4q c4h |")
    assert tc.notes[0].pitches == [60, 64]

    # Extended qualities: a thirteenth voices five tones.
    ext = Song().section("Q").voice("x")
    ext.harmony("C13 Fm11 G7b9", style="block")
    assert len(ext.notes[0].pitches) == 5

    # The full dynamic range from ppp to fff.
    dyn = Song().section("DY").voice("m")
    dyn.bars("!ppp c4q !fff d4q c4h |")
    assert dyn.notes[0].vel == 18 and dyn.notes[1].vel == 96

    # A tie on the final note is laissez vibrer: it rings past the end.
    lv = Song()
    lv.section("LV").voice("m").bars("c4h c4h~ |")
    lv.arrange("LV")
    lv.report()          # must not raise
    offs = [t for (t, k, _, _, _) in lv.events() if k == "off"]
    assert max(offs) > 1920

    # harmony(avoid=) drops chord tones that double the melody.
    av = Song()
    asec = av.section("AV")
    mel = asec.voice("rh")
    mel.bars("e4w |")
    asec.voice("lh").harmony("C", style="block", avoid=mel)
    classes = {p % 12 for p in asec.voices[1].notes[0].pitches}
    assert 4 not in classes and {0, 7} <= classes

    # soft() emits an una-corda pedal event.
    sp = Song()
    sp.section("SP").voice("m").bars("c4w |")
    sp.sections["SP"].soft()
    sp.arrange("SP")
    assert "cc67" in {k for (_, k, _, _, _) in sp.events()}

    # events() exposes the raw stream; count_in taps per beat.
    ev = Song(tempo=120)
    ev.section("EV").voice("m").bars("c4q e4q g4q c5q |")
    ev.arrange("EV")
    assert any(k == "on" for (_, k, _, _, _) in ev.events())
    assert len(ev._count_in_taps(4)) == 8

    # report() duration integrates a ritardando (slower than base).
    dur = Song(tempo=120)
    dur.section("DR").voice("m").bars("c4w | c4w | c4w | c4w |")
    dur.ritardando("DR", 1, 4, 60)
    dur.arrange("DR")
    assert dur.report()["duration_s"] > 8.0

    # A full first bar is legal even when a pickup is declared.
    pu = Song(pickup=1)
    puv = pu.section("PU").voice("m")
    puv.bars("c4q d4q e4q f4q | g4q a4q b4q c5q |")
    assert abs(puv.total_beats() - 8.0) < 1e-9

    # Query helpers: chord and scale pitches.
    assert chord_pitches("Cmaj9") == [60, 64, 67, 71, 74]
    assert chord_pitches("C/G")[0] % 12 == 7
    assert scale_pitches("C") == [60, 62, 64, 65, 67, 69, 71]
    assert scale_pitches("Am") == [69, 71, 72, 74, 76, 77, 79]

    # Chromatic transpose shifts pitches and relabels the key.
    tr = Song(key="C")
    tr.section("A").voice("m").bars("c4q e4q g4q c5q |")
    tr.arrange("A")
    tr.transpose(3)
    assert tr.sections["A"].voices[0].notes[0].pitches == [63]
    assert tr.key == "Eb"

    # Harmony voicings: shell = root/third/seventh; drop2 spreads wider.
    sh = Song().section("S").voice("x")
    sh.harmony("Cmaj7", style="block", voicing="shell")
    assert sorted(p % 12 for p in sh.notes[0].pitches) == [0, 4, 11]
    try:
        Song().section("U").voice("x").harmony("C", voicing="bogus")
        raise AssertionError("voicing check did not fire")
    except CompositionError as e:
        assert "voicing" in str(e)

    print("tests passed")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _test()
    elif "--guide" in sys.argv:
        print(GUIDE)
    elif "--cheatsheet" in sys.argv:
        print(CHEATSHEET)
    else:
        print(__doc__)
