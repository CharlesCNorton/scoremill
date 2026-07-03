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
  Tuplet    {c4 d4 e4}q — members divide the span equally. Members do
            not carry duration letters.
  Grace     +d5 — sounds approximately 60 ticks before the next note;
            multiple grace notes stack.
  Tie       trailing ~ joins the note to the next note, which must
            repeat the same pitch (validated).
  Marks     > accent, ' staccato, _ legato, ^ fermata (extends sounding
            length; written time unchanged), & rolled chord, % trill
            (diatonic upper neighbor in thirty-seconds).
  Dynamics  !pp !p !mp !mf !f !ff set the level until changed; "cresc"
            and "dim" interpolate toward the next dynamic mark, which
            must exist (validated).
  Barline   | asserts the bar is exactly full. Errors report the
            difference and the offending bar's tokens. Song(pickup=N)
            permits a short first bar.

MOTIF TRANSFORMS (string to string)

  shift(frag, n)           diatonic transposition by n scale steps;
                           explicit alterations travel with their degree
  invert(frag, axis)       diatonic inversion about an axis pitch;
                           alterations are mirrored (# becomes b)
  retro(frag)              retrograde (fragment must not contain
                           barlines, dynamics, or ties)
  stretch(frag, factor)    augmentation (2) or diminution (0.5)

HARMONY

  voice.harmony("C Am7 F G7", style=..., voicing=..., slots=...)
  Qualities: m 7 maj7 m7 6 m6 dim dim7 m7b5 aug sus2 sus4 9 maj9 m9
  add9; slash bass (C/G); "." repeats the previous symbol. slots="half"
  places two symbols per bar. voicing="smooth" selects inversions that
  minimize movement from the previous chord.
  Styles: block root fifth waltz alberti arp broken stride.

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

  Song(swing=0.62, humanize=2, expressive=True)
  section.rubato(depth, phrase); section.pedal("bar"|"half")
  s.tempo_change(section, bar, bpm)              # step change
  s.ritardando(section, bar_from, bar_to, bpm)   # linear ramp

ANALYSIS

  describe() prints a summary. lint() returns counterpoint findings
  (unison collisions, parallel fifths and octaves). report() returns a
  dictionary of sections, voices, ranges, density, duration, and lint
  results, suitable for programmatic assertions.

RECOMMENDED WORKFLOW

  1. Write sections with bars() and harmony(); structural errors are
     reported at parse time.
  2. Review describe(), lint(), and report().
  3. Audition with play(only=<section>).
  4. Render with save(<path>).
"""
import re
import sys

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
DYN = {"pp": 28, "p": 38, "mp": 48, "mf": 58, "f": 70, "ff": 84}

CHORD_QUALITY = {
    "": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "dim": (0, 3, 6),
    "dim7": (0, 3, 6, 9), "m7b5": (0, 3, 6, 10),
    "sus4": (0, 5, 7), "sus2": (0, 2, 7), "aug": (0, 4, 8),
    "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9),
    "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14),
    "m9": (0, 3, 7, 10, 14), "add9": (0, 4, 7, 14),
}

MARKS = "~>'_^&%"
NOTE_RE = re.compile(
    r"^([a-gr])(##|bb|#|b|n)?(\d)?([whqest]\.?)?([" + MARKS + r"]*)$")
CHORD_RE = re.compile(
    r"^\[([^\]]+)\]([whqest]\.?)?([" + MARKS + r"]*)$")
TUPLET_RE = re.compile(r"^\{([^}]+)\}([whqest]\.?)?$")
SYM_RE = re.compile(
    r"^([A-G])(#|b)?"
    r"(maj9|maj7|m7b5|dim7|add9|m9|m7|m6|sus4|sus2|aug|dim|m|9|7|6)?"
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
        parts = [_map_note_token(t, fn, state) for t in inner.split()]
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
                if first_bar and self.song.pickup:
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
                    raise CompositionError(
                        f"voice '{self.name}' bar {bar_no}: has "
                        f"{beats_in_bar} beats, expected {want} — {how}.\n"
                        f"    bar was: {' '.join(bar_tokens)}")
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
                        f"unknown dynamic '{raw}' (use !pp !p !mp !mf !f !ff)")
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
            members = inner.split()
            if not members:
                raise CompositionError(f"empty tuplet '{raw}'")
            span = self._beats(durtok)
            each = span / len(members)
            for t in members:
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
            gate = 1.55
        if "%" in marks:
            if len(pitches) != 1:
                raise CompositionError("trill '%' works on single notes")
            main = pitches[0]
            upper = self._diatonic_upper(main)
            n32 = max(2, int(beats / 0.125))
            for i in range(n32 - 1):
                self.notes.append(Note([main if i % 2 == 0 else upper],
                                       0.125, max(20, vel - 6), gate=0.9))
            rem = beats - (n32 - 1) * 0.125
            self.notes.append(Note([main], rem, vel, gate))
            return
        self.notes.append(Note(pitches, beats, min(127, vel), gate,
                               tie="~" in marks, roll="&" in marks))

    # ── harmony ──────────────────────────────────────────
    def harmony(self, symbols, style="block", slots="bar", octave=3,
                voicing="plain"):
        """Render chord symbols as an accompaniment figure. `octave`
        places the chord roots and is independent of the octave the
        voice uses for melodic input."""
        slot_beats = self.bpb if slots == "bar" else self.bpb / 2
        prev_sym = None
        prev_voicing = None
        for sym in symbols.split():
            if sym == "|":
                continue
            if sym == ".":
                if prev_sym is None:
                    raise CompositionError("harmony: '.' with no prior chord")
                sym = prev_sym
            prev_sym = sym
            tones = self._chord_pitches(sym, octave)
            if voicing == "smooth" and prev_voicing:
                tones = [tones[0]] + self._lead(prev_voicing[1:], tones[1:])
            prev_voicing = tones
            self._figure(tones, style, slot_beats)
        return self

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
        if bass_l:
            tones.insert(0, 12 * octave + _pc(bass_l.lower(), bass_a))
        return tones

    def _figure(self, tones, style, beats):
        v = self._vel
        root, top = tones[0], tones[1:]
        if style == "block":
            self.notes.append(Note(tones, beats, v))
        elif style == "root":
            self.notes.append(Note([root], beats, v))
        elif style == "fifth":
            self.notes.append(Note([root, root + 7], beats, v))
        elif style == "waltz":
            self.notes.append(Note([root], 1.0, v))
            chord = top if len(top) >= 2 else [root + 4, root + 7]
            for _ in range(int(beats) - 1):
                self.notes.append(Note(chord, 1.0, max(20, v - 8)))
        elif style == "alberti":
            third = tones[1] if len(tones) > 1 else root + 4
            fifth = tones[2] if len(tones) > 2 else root + 7
            seq = [root, fifth, third, fifth]
            for i in range(int(beats * 2)):
                self.notes.append(Note([seq[i % 4]], 0.5, max(20, v - 6)))
        elif style == "arp":
            seq = tones + [root + 12]
            for i in range(int(beats * 2)):
                self.notes.append(Note([seq[i % len(seq)]], 0.5,
                                       max(20, v - 6)))
        elif style == "stride":
            chord = [t + 12 for t in top] or [root + 16, root + 19]
            use_fifth = False
            b = 0.0
            while b < beats - 1e-6:
                bass = root - 12 + (7 if use_fifth else 0)
                use_fifth = not use_fifth
                self.notes.append(Note([bass], 1.0, v + 4))
                b += 1
                if b < beats - 1e-6:
                    self.notes.append(Note(chord, 1.0, max(20, v - 10),
                                           gate=0.5))
                    b += 1
        elif style == "broken":
            self.notes.append(Note([root], 1.0, v))
            self.notes.append(Note([root + 7], 1.0, max(20, v - 6)))
            rest = beats - 2
            if rest > 0:
                self.notes.append(Note([t + 12 for t in top] or
                                       [root + 12], rest, max(20, v - 6)))
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
        self.rubato_depth = 0.0
        self.rubato_phrase = 2

    def voice(self, name, vel=50, octave=4, program=0, channel=0):
        v = Voice(f"{self.name}.{name}", self.song, vel, octave,
                  key=self.key, program=program, channel=channel,
                  bpb=self.bpb)
        self.voices.append(v)
        return v

    def pedal(self, mode="bar"):
        self.pedal_mode = mode
        return self

    def rubato(self, depth=0.05, phrase=2):
        self.rubato_depth = depth
        self.rubato_phrase = phrase
        return self

    def variant(self, name, vel_scale=1.0):
        """Return a copy of this section with velocities scaled."""
        clone = self.song.section(name, key=self.key)
        clone.bpb = self.bpb
        clone.pedal_mode = self.pedal_mode
        clone.rubato_depth = self.rubato_depth
        clone.rubato_phrase = self.rubato_phrase
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
                    if nxt is None or nxt.pitches != n.pitches:
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
                 humanize=0, swing=0.5, expressive=True,
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
        self.expressive = expressive
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
        if tick % TPB == TPB // 2:
            return int((self.swing - 0.5) * TPB)
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
                            off_t = start + int(length * n.gate)
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
            bpm_at, has_plan = self._base_bpm_fn(sec_name, sec)
            total = int(sec_len * TPB)
            if sec.rubato_depth > 0:
                phrase_ticks = int(sec.rubato_phrase * bar_ticks)
                pos = 0
                while pos < total:
                    x = (pos % phrase_ticks) / phrase_ticks
                    mult = 1.0 + sec.rubato_depth * math.sin(math.pi * x)
                    if x > 0.85:
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
            elif kind == "cc64":
                tr.append(mido.Message("control_change", channel=ch,
                                       control=64, value=a, time=dt))
            elif kind == "tempo":
                tr.append(mido.MetaMessage(
                    "set_tempo", tempo=mido.bpm2tempo(a), time=dt))
        tr.append(mido.MetaMessage("end_of_track",
                                   time=max(0, total - last)))
        return mid

    def save(self, path, only=None):
        """Write the song to a standard MIDI file and return the path."""
        self._midifile([only] if only else None).save(path)
        return path

    def play(self, port=None, only=None):
        """Stream the song to a MIDI output in real time.

        `port` selects an output by case-insensitive substring of its
        mido port name; when omitted, the first output that is not a
        software through-port is used. Sends all-notes-off and releases
        the pedal on every used channel when playback ends or is
        interrupted. Returns the name of the port used."""
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
                for msg in mid.play():
                    out.send(msg)
            finally:
                for ch in channels:
                    out.send(mido.Message("control_change", channel=ch,
                                          control=123, value=0))
                    out.send(mido.Message("control_change", channel=ch,
                                          control=64, value=0))
        return chosen

    # ── feedback for agents ──────────────────────────────
    def lint(self, quiet=False):
        """Check counterpoint across each section's voices. Returns a
        list of findings; prints them unless quiet=True."""
        all_issues = []
        order = self.order or list(self.sections)
        seen = set()
        for sec_name in order:
            if sec_name in seen:
                continue
            seen.add(sec_name)
            sec = self.sections[sec_name]
            issues = []
            lines = []
            for v in sec.voices:
                t = 0.0
                line = []
                for n in v.notes:
                    if n.grace:
                        continue
                    if n.pitches:
                        line.append((round(t, 4), n.beats, tuple(n.pitches)))
                    t += n.beats
                lines.append((v.name, line))
            for i in range(len(lines)):
                for j in range(i + 1, len(lines)):
                    n1, l1 = lines[i]
                    n2, l2 = lines[j]
                    onsets2 = {t: p for t, _, p in l2}
                    pairs = [(t, p1, onsets2[t]) for t, _, p1 in l1
                             if t in onsets2]
                    for (t, p1, p2) in pairs:
                        if set(p1) & set(p2):
                            issues.append(
                                f"UNISON collision {n1}/{n2} at beat {t}: "
                                f"{set(p1) & set(p2)}")
                    for k in range(1, len(pairs)):
                        _, a0, b0 = pairs[k - 1]
                        t1, a1, b1 = pairs[k]
                        iv0 = abs(max(a0) - max(b0)) % 12
                        iv1 = abs(max(a1) - max(b1)) % 12
                        moved = max(a0) != max(a1) and max(b0) != max(b1)
                        if moved and iv0 == iv1 and iv0 in (0, 7):
                            kind = "octaves" if iv0 == 0 else "fifths"
                            issues.append(
                                f"parallel {kind} {n1}/{n2} at "
                                f"beat {t1} ({max(a1)}/{max(b1)})")
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
        ranges, note density, duration, and lint findings."""
        order = self.order or list(self.sections)
        out = {"tempo": self.tempo, "key": self.key,
               "beats_per_bar": self.beats_per_bar,
               "swing": self.swing, "sections": [], "lint": []}
        total_beats = 0.0
        for name in order:
            sec = self.sections[name]
            ln = sec.length_beats()
            total_beats += ln
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
                "pedal": sec.pedal_mode, "rubato": sec.rubato_depth,
                "voices": voices,
            })
        out["duration_s"] = round(total_beats / self.tempo * 60, 1)
        out["lint"] = self.lint(quiet=True)
        return out

    def describe(self):
        order = self.order or list(self.sections)
        total_beats = 0.0
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
            total_beats += ln
            extras = []
            if sec.key:
                extras.append(f"key={sec.key}")
            if sec.bpb != self.beats_per_bar:
                extras.append(f"{sec.bpb}-beat bars")
            if sec.pedal_mode:
                extras.append(f"pedal={sec.pedal_mode}")
            if sec.rubato_depth:
                extras.append(f"rubato={sec.rubato_depth}")
            chans = {v.channel for v in sec.voices}
            if chans != {0}:
                extras.append(f"channels={sorted(chans)}")
            print(f"  [{name}] {ln / sec.bpb:.1f} bars, "
                  f"{len(sec.voices)} voices"
                  + (f" ({', '.join(extras)})" if extras else ""))
        print(f"  total ~ {total_beats / self.tempo * 60:.0f}s")


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
    A.voice("lh", vel=36, octave=2).harmony(
        "Am G Am E7", style="broken", voicing="smooth")
    A.pedal("bar")
    s.ritardando("A", 3, 4, 70)             # smooth final rit
    s.arrange("A")

    s.describe()                            # printed summary
    print(s.report()["duration_s"])         # structured summary
    s.lint()                                # counterpoint findings
    s.play()                                # send to the MIDI device

WORKFLOW: write bars() (validated at parse time); review describe(),
lint(), and report(); audition with play(only=...); iterate; publish
with save(). Bar errors state the beat difference and show
the offending bar.
'''

CHEATSHEET = '''
PITCH  c..b [+ # b n] [+octave]   sticky octave; key sig applies
DUR    w h q e s t [+ .]          sticky;  r = rest (re = eighth rest)
CHORD  [c4 e g]h     TUPLET {c d e}q     GRACE +d5     TIE c5h~
MARKS  > accent  ' stacc  _ legato  ^ fermata  & roll  % trill
DYN    !pp !p !mp !mf !f !ff   cresc/dim toward next !dyn
BAR    | must be exactly full (pickup= allows short first bar)
HARMONY voice.harmony("C Am7 F G7", style=block|root|fifth|waltz|
        alberti|arp|broken|stride, voicing=plain|smooth, slots=bar|half)
TRANSFORMS shift(frag,n) invert(frag,axis) retro(frag) stretch(frag,2)
SONG   Song(tempo,time,key,pickup,humanize,swing,expressive)
       .section(name,key=,time=) .arrange("A A B A")
       .tempo_change(sec,bar,bpm) .ritardando(sec,from,to,bpm)
       .describe() .lint() .report() .play(port=, only=) .save(path)
SECTION .voice(name,vel,octave,program,channel) .pedal() .rubato()
        .variant(name, vel_scale)
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

    # lint() detects parallel fifths between two voices.
    par = Song()
    par.section("X").voice("a").bars("c4q d4q e4q f4q |")
    par.sections["X"].voice("b").bars("g4q a4q b4q c5q |")
    par.arrange("X")
    findings = par.lint(quiet=True)
    assert any("parallel fifths" in f for f in findings), findings

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
