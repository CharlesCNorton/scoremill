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
  Duration  trailing letter w h q e s t x (whole through sixty-fourth),
            with up to two dots (q. = 1.5 beats, q.. = 1.75). Persists
            until changed: "c4q d e f gh" is three further quarters,
            then a half. "r" denotes a rest.
  Repeat    c4e*4 writes a token four times; (c4e d4e)*3 repeats a
            group, which may hold barlines: (c4w |)*8.
  Chord     [c4 e g]h — simultaneous pitches with a shared duration.
  Tuplet    {c4 d4 e4}q — members divide the span equally. Members may
            be chords ({[c4 e4] d4 [c4 e4]}q) or tuplets of their own
            ({c4 {d4 e4 f4} g4}q), which divide their member's share,
            and do not carry duration letters.
  Grace     +d5 — sounds approximately 60 ticks before the next note;
            multiple grace notes stack.
  Tie       trailing ~ joins the note to the next note, which must
            repeat the same pitch (validated). A tie on a voice's
            final note means laissez vibrer: the note rings past its
            written length.
  Marks     > accent, ' staccato, _ legato, ^ fermata (the moment is
            held: time stretches by Song(fermata=) under the note, or
            under a rest for a general pause), & rolled chord, % trill
            (diatonic upper neighbor at Song(trill_rate=) beats per
            alternation).
  Pedal     ped presses the sustain pedal at the next note, or changes
            it there (lifted just before, pressed just after); lift
            releases it. A section ends with the pedal lifted.
  Dynamics  !ppp !pp !p !mp !mf !f !ff !fff set the level until
            changed; "cresc" and "dim" interpolate toward the next
            dynamic mark, which must exist (validated).
  Barline   | asserts the bar is exactly full. Errors report the
            difference and the offending bar's tokens. Song(pickup=N)
            permits a short first bar of exactly N beats; a full first
            bar remains legal. In a section that opens with a pickup,
            bar numbers, the pedal, tempo changes, swing, and the
            downbeat lean all count from the first downbeat.
  Meter     M:3/4 at the start of a bar changes the meter from that
            bar on, for every voice of the section;
            section.time_change(bar, "3/4") declares the same change.
            Bar checks, bar numbers, pedaling by the bar,
            harmony(slots="bar"), and the engraving follow the meters.
  Onset     c5e@3 places a note's onset at beat 3 from the voice's
            start, after voice.absolute_onsets(); a gap is filled with
            a rest (the marks and graces written before the note stay
            with it), and an onset that earlier material has already
            passed is an error.
  Drums     section.drums() is a General MIDI percussion voice on
            channel 10, written with drum names in place of pitches:
            "bde hh sn hh | [bd hh]q ..." (names in DRUMS).

MOTIF TRANSFORMS (string to string)

  shift(frag, n)           diatonic transposition by n scale steps;
                           explicit alterations travel with their degree
  invert(frag, axis)       diatonic inversion about an axis pitch;
                           alterations are mirrored (# becomes b)
  retro(frag)              retrograde; graces stay with their notes and
                           tuplet members reverse (no barlines,
                           dynamics, or ties inside)
  stretch(frag, factor)    augmentation (2) or diminution (0.5)
  rebar(frag, beats)       insert barlines every N beats, following
                           sticky durations; errors if a token would
                           cross a barline
  transpose(frag, n, key)  chromatic transposition by n semitones,
                           spelled by interval with explicit accidentals
  double(frag, degrees)    every note doubled a diatonic interval away:
                           7 the octave above, -7 below, -2 in thirds
  harmonize(frag, symbols, key, voices=3, bass=)
                           each melody note the top of a chord, the
                           added notes chosen over the whole passage so
                           no voices, nor any against the bass, move in
                           consecutive fifths or octaves
  map_notes(frag, fn, key) each note rewritten by fn, which receives a
                           Mapped (pitch, beats, at, bar) and returns a
                           pitch, a list of pitches (a chord), [] (a
                           rest), or None (unchanged)

QUERY HELPERS

  chord_pitches("Cmaj9"), scale_pitches("Am"), note_pitch("c#5", key=),
  note_name(61, key="Dm") -> "c#4" (spelled for the key, accidental
  explicit), transpose_chords("C G7/B", 1) -> "Db Ab7/C",
  chord_tone_below(72, "Dm7") -> 69 (the highest chord tone at least a
  minor third down), same_shape(a, b) (the same rhythm and intervals,
  one an exact transposition of the other).

HARMONY

  voice.harmony("C Am7 F G7", style=..., voicing=..., slots=...,
                avoid=..., pattern=..., unit=...)
  Qualities: m 7 maj7 m7 6 m6 dim dim7 m7b5 aug sus2 sus4 9 maj9 m9
  add9 mmaj7 m11 7sus4 9sus4 7b5 7#5 7b9 7#9 11 13; slash bass (C/G);
  "." repeats the previous symbol. slots="half" places two symbols per
  bar, and a number places one symbol per that many beats (slots=1
  splits a 3/4 bar 1 + 2 with "Dm A7 ."). voicing="smooth" selects
  inversions that minimize movement from
  the previous chord. avoid=<voice> drops accompaniment chord tones
  that would double that voice's pitch classes on a shared onset and
  re-octaves figure tones that would collide at the unison. When the
  song has a pickup and the voice is empty, harmony inserts the pickup
  rest itself; the rest gives way when the voices written by hand open
  on a downbeat, whichever is written first.
  Styles: block root fifth waltz alberti arp broken stride (waltz,
  stride, and broken fill fractional meters). pattern= replaces the
  style with any figure: indices into the chord's tone ladder (its
  tones stacked up by octaves, a slash bass at 0), stepped `unit` beats
  at a time: pattern="0 2 3 4 3 2", unit=1/3 is a rolling triplet
  arpeggio; "0+4" strikes two ladder tones, "r" rests, and a step may
  carry its own length, as the habanera "0:e. 4:s 2+3:e 2+3:e" does.
  Symbols repeat with *: "Am*4".

STRUCTURE

  s = Song(tempo=92, time="3/4", key="F", pickup=1, title="Evening",
           composer="An Agent")              # title/composer: MIDI and LilyPond
  A = s.section("A")
  J = s.section("Jig", key="Bb", time="6/8")     # per-section overrides
  J.time_change(9, "9/8")                        # its meter from bar 9 on
  A.voice("rh", vel=52).bars("...")
  A.voice("str", program=48, channel=1)          # second timbre; a channel
                                                 # may change program by section
  echo = A.variant("A2", vel_scale=0.85)
  s.arrange("A A2 Jig A")
  s.save("piece.mid"); s.play(); s.play(only="Jig", port="Synth")

EXPRESSION

  Song(swing=0.62, swing_unit="eighth"|"sixteenth", humanize=2,
       expressive=True, fermata=1.55, trill_rate=0.125)
  section.rubato(depth, phrase, shape="arch"|"cradle")
  section.pedal("bar"|"half"|beats); section.soft()   # una corda
  section.swing(0.66, "eighth")                  # the section's own swing
  Song(dynamics={"p": 45, "f": 80})              # retune the levels
  s.tempo_change(section, bar, bpm)              # step change
  s.ritardando(section, bar_from, bar_to, bpm)   # linear ramp
  A tempo plan belongs to its section: every section begins at the
  song tempo.

ANALYSIS

  describe() prints a summary. lint() returns counterpoint findings
  located by bar and beat: unison collisions (including strikes
  against held notes) and consecutive parallel fifths and octaves on
  both the top and bottom lines of each voice pair.
  lint(mode="homophonic") keeps only collisions, for textures that
  double melody and accompaniment by design; lint(mode="strict") adds
  voice crossings, unresolved leading tones, unprepared dissonances,
  tessitura, and unrolled chords wider than a tenth; lint(only="Fugue")
  checks one section. report() returns
  a dictionary of sections, voices, ranges, density, per-voice pitch
  metrics, duration (tempo map included), lint results, and rubs,
  suitable for assertions. chords(per="beat"|"half"|"bar") names the harmony
  that sounds, window by window, so the progression can be checked
  without listening. rubs() finds notes of different voices a minor
  second, major seventh, or minor ninth apart that ring together,
  following the pedaling, since a note held by the pedal keeps
  sounding. find(frag) lists every place a motif sounds at any exact
  transposition, so a variation can be checked for leaving it intact.
  to_lilypond(path) engraves the song as LilyPond source with
  dynamics, hairpins, articulations, trills, pedaling, and tempo marks.
  Song.from_midi(path) reads a MIDI file into a Song, so all of these
  apply to music scoremill did not write.

RAW ACCESS

  song.events() returns the fully expressive event stream as sorted
  (tick, kind, channel, a, b) tuples, kind in {"on", "off", "cc64",
  "cc67", "tempo"}, at TPB (480) ticks per beat. Each key is well
  formed on its channel: a note is released no later than the next
  strike of the same pitch, and strikes of one key at one tick merge.
  play(count_in=N) taps N beats before the music; play(progress=fn)
  calls fn(msg) per message. Notes may also be appended to a Voice
  directly; direct injection bypasses notation validation, and
  Note(..., vels=[...]) gives each pitch of a chord its own velocity.

RECOMMENDED WORKFLOW

  1. Write sections with bars() and harmony(); structural errors are
     reported at parse time.
  2. Review describe(), lint(), and report().
  3. Audition with play(only=<section>).
  4. Render with save(<path>): a type 1 MIDI file with a conductor
     track and a track per voice role (tracks=False: one track).
"""
from __future__ import annotations

import itertools
import re
import sys
import time
from collections import namedtuple

import mido

__version__ = "0.8.1"

TPB = 480
PIANO_LO, PIANO_HI = 21, 108
_MIN_TICKS = 20            # the shortest note the renderer sounds

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
DUR = {"w": 4.0, "h": 2.0, "q": 1.0, "e": 0.5, "s": 0.25, "t": 0.125,
       "x": 0.0625}
DUR_ORDER = "whqestx"
DYN = {"ppp": 18, "pp": 28, "p": 38, "mp": 48, "mf": 58, "f": 70,
       "ff": 84, "fff": 96}

# General MIDI percussion (channel 10): short drum names -> note numbers.
DRUMS = {
    "bd": 36, "kick": 36, "bd2": 35, "sn": 38, "snare": 38, "sd": 38,
    "rim": 37, "clap": 39, "esn": 40, "lt": 45, "mt": 47, "ht": 50,
    "lft": 41, "hft": 43, "hh": 42, "hc": 42, "ho": 46, "hp": 44,
    "cr": 49, "crash": 49, "cr2": 57, "sp": 55, "ch": 52, "rd": 51,
    "ride": 51, "rb": 53, "cb": 56, "tamb": 54, "clave": 75, "wood": 76,
    "tri": 81,
}
_DRUM_NAMES = sorted(DRUMS, key=len, reverse=True)

# LilyPond note spelling (english note names) and durations.
_LY_SHARP = {0: "c", 1: "cs", 2: "d", 3: "ds", 4: "e", 5: "f", 6: "fs",
             7: "g", 8: "gs", 9: "a", 10: "as", 11: "b"}
_LY_FLAT = {0: "c", 1: "df", 2: "d", 3: "ef", 4: "e", 5: "f", 6: "gf",
            7: "g", 8: "af", 9: "a", 10: "bf", 11: "b"}
_LY_DUR = {4.0: "1", 6.0: "1.", 2.0: "2", 3.0: "2.", 1.0: "4", 1.5: "4.",
           0.5: "8", 0.75: "8.", 0.25: "16", 0.375: "16.", 0.125: "32",
           0.1875: "32.", 0.0625: "64", 0.09375: "64.", 7.0: "1..",
           3.5: "2..", 1.75: "4..", 0.875: "8..", 0.4375: "16..",
           0.21875: "32..", 0.109375: "64..", 0.03125: "128",
           0.046875: "128.", 0.0546875: "128.."}

# LilyPond drum-mode names for the General MIDI percussion notes in DRUMS.
_LY_DRUM = {35: "bda", 36: "bd", 37: "ss", 38: "sn", 39: "hc", 40: "sne",
            41: "tomfl", 42: "hh", 43: "tomfh", 44: "hhp", 45: "toml",
            46: "hho", 47: "tomml", 49: "cymc", 50: "tomh", 51: "cymr",
            52: "cymch", 53: "rb", 54: "tamb", 55: "cyms", 56: "cb",
            57: "cymcb", 75: "cl", 76: "wbh", 81: "trio"}


def _ly_octave(octv: int) -> str:
    return "'" * (octv - 3) if octv >= 3 else "," * (3 - octv)


def _ly_pitch(midi: int, flat: bool) -> str:
    name = (_LY_FLAT if flat else _LY_SHARP)[midi % 12]
    return name + _ly_octave(midi // 12 - 1)


def _ly_spelled(letter: str, alter: int, octv: int) -> str:
    """A written spelling in LilyPond's english names: ef', css''."""
    return (letter + ("s" * alter if alter > 0 else "f" * -alter)
            + _ly_octave(octv))

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
DUR_RX = r"[whqestx]\.{0,2}"           # a duration letter, up to two dots
NOTE_RE = re.compile(
    r"^([a-gr])(##|bb|#|b|n)?(\d)?(" + DUR_RX + r")?([" + MARKS + r"]*)$")
CHORD_RE = re.compile(
    r"^\[([^\]]+)\](" + DUR_RX + r")?([" + MARKS + r"]*)$")
TUPLET_RE = re.compile(r"^\{(.+)\}(" + DUR_RX + r")?$", re.S)
METER_RE = re.compile(r"^M:(\d+)/(\d+)$")     # a meter change: M:3/4
_TUPLET_IDS = itertools.count(1)              # tuplet group ids, for engraving
GROUP_RE = re.compile(r"\(([^()]*)\)\*(\d+)")
REPEAT_RE = re.compile(r"^(.+)\*(\d+)$")
PEDAL_MARKS = ("ped", "lift")
SYM_RE = re.compile(
    r"^([A-G])(#|b)?"
    r"(mmaj7|maj9|maj7|m7b5|dim7|add9|9sus4|7sus4|sus4|sus2"
    r"|m11|m9|m7|m6|7b9|7#9|7b5|7#5|aug|dim|m|13|11|9|7|6)?"
    r"(?:/([A-G])(#|b)?)?$")


class CompositionError(Exception):
    pass


def _resolve_key(key: str) -> str:
    """Accept major ('Eb') or minor ('Cm') names; return signature key."""
    if key in KEYS:
        return key
    if key in RELATIVE_MAJOR:
        return RELATIVE_MAJOR[key]
    raise CompositionError(
        f"unknown key '{key}' — majors {sorted(KEYS)} or minors "
        f"{sorted(RELATIVE_MAJOR)}")


# Chromatic tonic names for relabeling a transposed key. Every supported
# key's tonic maps to a pitch class; the reverse tables spell each major
# and minor key the way KEYS and RELATIVE_MAJOR name it.
_KEY_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5,
           "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "Bb": 10,
           "B": 11}
_PC_KEY = {0: "C", 1: "Db", 2: "D", 3: "Eb", 4: "E", 5: "F", 6: "F#",
           7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B"}
_PC_MINOR = {0: "Cm", 1: "C#m", 2: "Dm", 3: "Ebm", 4: "Em", 5: "Fm",
             6: "F#m", 7: "Gm", 8: "G#m", 9: "Am", 10: "Bbm", 11: "Bm"}


def _transpose_key(key: str, semitones: int) -> str:
    """Relabel a key name (major 'Eb' or minor 'Cm') by semitones,
    keeping the mode and choosing a spelling _resolve_key accepts. A
    shift by whole octaves keeps the name; unknown names pass through
    unchanged."""
    minor = key.endswith("m")
    root = key[:-1] if minor else key
    if root not in _KEY_PC or semitones % 12 == 0:
        return key
    pc = (_KEY_PC[root] + semitones) % 12
    return _PC_MINOR[pc] if minor else _PC_KEY[pc]


def _chord_tones(sym: str, octave: int, where: str) -> tuple[list[int], bool]:
    """Parse a chord symbol into (tones, has_bass). A slash bass, when
    present, is the first tone and sits an octave below the root. `where`
    labels the error site. The single chord-symbol parser, shared by
    chord_pitches() and Voice.harmony()."""
    m = SYM_RE.match(sym)
    if not m:
        raise CompositionError(
            f"{where}: bad chord symbol '{sym}' (qualities: "
            f"{' '.join(sorted(q for q in CHORD_QUALITY if q))})")
    root_l, root_a, qual, bass_l, bass_a = m.groups()
    root = 12 * (octave + 1) + _pc(root_l.lower(), root_a)
    tones = [root + iv for iv in CHORD_QUALITY[qual or ""]]
    has_bass = bool(bass_l)
    if bass_l:
        tones.insert(0, 12 * octave + _pc(bass_l.lower(), bass_a))
    return tones, has_bass


def chord_pitches(symbol: str, octave: int = 4) -> list[int]:
    """The MIDI pitches of a chord symbol ('Cmaj9', 'D7b9', 'F/A'), with
    a slash bass first when present. A query helper for building
    accompaniment or checking harmony without a Song."""
    return _chord_tones(symbol, octave, "chord_pitches")[0]


def scale_pitches(key: str, octave: int = 4) -> list[int]:
    """The seven MIDI pitches of a key's diatonic scale, ascending from
    the tonic. Major keys give the major scale; minor keys ('Am') give
    the natural minor. A query helper for melody construction."""
    sig = _resolve_key(key)
    tonic = key[0].lower()
    start = LETTERS.index(tonic)
    return [12 * (octave + 1) + _pc(LETTERS[(start + i) % 7], "", sig)
            + 12 * ((start + i) // 7) for i in range(7)]


def note_pitch(name: str, key: str = "C") -> int:
    """The MIDI pitch of a written note with its octave ('c#5', 'bb3');
    a letter without an accidental takes `key`'s signature, as it would
    in a voice in that key."""
    m = NOTE_RE.match(name)
    if (not m or m.group(1) == "r" or not m.group(3) or m.group(4)
            or m.group(5)):
        raise CompositionError(
            f"note_pitch: write one pitch with its octave, like 'c#5' "
            f"(got {name!r})")
    return 12 * (int(m.group(3)) + 1) + _pc(m.group(1), m.group(2) or "",
                                             _resolve_key(key))


# The scale degree (0-6 letters above the tonic) that spells each
# semitone above the tonic: the second degree for a lowered second, the
# third for a minor or major third, the fourth for a raised fourth, the
# sixth for either sixth, the seventh for either seventh. The same table
# serves major and minor, since the alteration comes from the letter.
_CHROMA = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 5, 9: 5,
           10: 6, 11: 6}


def _spelling(pc: int, key: str) -> tuple[str, int]:
    """(letter, alteration) spelling pitch class pc in `key`."""
    _resolve_key(key)
    root = key[:-1] if key in RELATIVE_MAJOR else key
    start = LETTERS.index(root[0].lower())
    letter = LETTERS[(start + _CHROMA[(pc - _KEY_PC[root]) % 12]) % 7]
    return letter, (pc - STEP[letter] + 6) % 12 - 6


def note_name(pitch: int, key: str = "C") -> str:
    """Spell a MIDI pitch as a note name with an explicit accidental ('n'
    for natural), so it reads the same under any key signature. `key`
    chooses the spelling: its own scale degrees; in major the lowered
    second, third, sixth, and seventh and the raised fourth; in minor the
    Neapolitan second and the raised third, fourth, sixth, and seventh
    (a double accidental where the key needs one).
    note_name(61, "Dm") is 'c#4', note_name(63, "Dm") is 'eb4'."""
    letter, alter = _spelling(pitch % 12, key)
    octave = (pitch - alter - STEP[letter]) // 12 - 1
    return f"{letter}{_ALTER[alter]}{octave}"


def transpose_chords(symbols: str, semitones: int,
                     key: str | None = None) -> str:
    """Transpose chord symbols ('C G7/B Am*2 .') by semitones, for moving
    a progression that harmony() will figure. Roots and slash basses are
    spelled as `key` spells them (see note_name); with no key, as the key
    of the first transposed chord does, so 'C F/A' up a semitone reads
    'Db Gb/Bb'. '|', '.', and '*N' repeats pass through."""
    parsed = []
    for tok in symbols.split():
        if tok in ("|", "."):
            parsed.append(tok)
            continue
        rm = re.match(r"^(.+?)(\*\d+)?$", tok)
        sm = SYM_RE.match(rm.group(1))
        if not sm:
            raise CompositionError(f"transpose_chords: bad chord symbol "
                                   f"{rm.group(1)!r}")
        parsed.append((sm.groups(), rm.group(2) or ""))

    def moved(letter, acc):
        return (_pc(letter.lower(), acc or "") + semitones) % 12

    if key is None:
        first = next((p for p in parsed if p not in ("|", ".")), None)
        if first is not None:
            (root_l, root_a, qual, _bl, _ba), _rep = first
            pc = moved(root_l, root_a)
            minor = bool(qual) and qual.startswith("m") and not \
                qual.startswith("maj")
            key = _PC_MINOR[pc] if minor else _PC_KEY[pc]

    def name(letter, acc):
        pc = moved(letter, acc)
        if key:
            nl, alter = _spelling(pc, key)
            if abs(alter) <= 1:
                return nl.upper() + {-1: "b", 0: "", 1: "#"}[alter]
        return _PC_KEY[pc]

    out = []
    for p in parsed:
        if p in ("|", "."):
            out.append(p)
            continue
        (root_l, root_a, qual, bass_l, bass_a), rep = p
        out.append(name(root_l, root_a) + (qual or "")
                   + ("/" + name(bass_l, bass_a) if bass_l else "") + rep)
    return " ".join(out)


def _pc(letter: str, acc: str, key: str = "C") -> int:
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


def _dur_value(durtok: str) -> float:
    """Beats in a duration token: a letter and up to two dots."""
    return DUR[durtok[0]] * (2 - 0.5 ** durtok.count("."))


def _meter_beats(time: str) -> float:
    """Quarter-note beats in a bar of a time signature ('6/8' is 3.0),
    rejecting one MIDI cannot state (a denominator not a power of two)."""
    m = re.match(r"^(\d+)/(\d+)$", str(time).strip())
    if not m or int(m.group(1)) < 1 or int(m.group(2)) not in (
            1, 2, 4, 8, 16, 32, 64):
        raise CompositionError(
            f"bad time signature {time!r} — write it like '3/4' or '6/8', "
            f"the denominator a power of two")
    return int(m.group(1)) * 4.0 / int(m.group(2))


def _beats_name(x: float) -> str | None:
    """Return the duration-letter name for a beat value, if exact."""
    for sym, val in DUR.items():
        if abs(val - x) < 1e-9:
            return f"a '{sym}'"
        if abs(val * 1.5 - x) < 1e-9:
            return f"a dotted '{sym}.'"
        if abs(val * 1.75 - x) < 1e-9:
            return f"a double-dotted '{sym}..'"
    return None


def _on_grid(x: float, step: float) -> bool:
    """Whether x is a whole number of steps, within float tolerance."""
    r = x % step
    return min(r, step - r) < 1e-6


def _pickup_of(length: float, pickup: float, bpb: float) -> float:
    """The pickup a passage of `length` beats opens with: `pickup` when
    the passage is that pickup plus whole bars, else 0.0."""
    if (pickup and not _on_grid(length, bpb)
            and _on_grid(length - pickup, bpb)):
        return pickup
    return 0.0


# ════════════════════════ motif transforms ════════════════════════
def _times(count: str) -> int:
    n = int(count)
    if not 1 <= n <= 999:
        raise CompositionError(f"repeat count {n} is outside 1-999")
    return n


def _tokenize(text: str) -> list[str]:
    """Split notation into tokens, writing out repetitions first: a
    group '(c4e d4e)*3' (which may hold barlines) or a token 'c4e*4'."""
    while True:
        expanded = GROUP_RE.sub(
            lambda m: " ".join([m.group(1)] * _times(m.group(2))), text)
        if expanded == text:
            break
        text = expanded
    if "(" in text or ")" in text:
        raise CompositionError(
            "unbalanced group: write a repeated group as '(c4e d4e)*3'")
    toks = []
    for tok in _split(text):
        m = REPEAT_RE.match(tok)
        toks.extend([m.group(1)] * _times(m.group(2)) if m else [tok])
    return toks


def _split(text: str) -> list[str]:
    """Split notation on whitespace, keeping a tuplet (whose braces may
    nest) or a chord whole, with the duration and marks after it."""
    toks, i, n = [], 0, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        j = i
        if text[i] == "{":
            depth = 0
            while j < n:
                depth += {"{": 1, "}": -1}.get(text[j], 0)
                if depth == 0:
                    break
                j += 1
            if j >= n:
                raise CompositionError(
                    f"unbalanced tuplet braces in '{text[i:i + 40]}'")
            j += 1
        elif text[i] == "[":
            j = text.find("]", i)
            if j < 0:
                raise CompositionError(
                    f"unbalanced chord bracket in '{text[i:i + 40]}'")
            j += 1
        while j < n and not text[j].isspace() and text[j] not in "{[":
            j += 1
        toks.append(text[i:j])
        i = j
    return toks


def _classify(tok: str):
    """Classify one notation token. The single point that decides what a
    token is, so the recognition rules live in one place instead of being
    re-derived in every parser and transform. Returns (kind, match, grace):
    kind is one of 'bar', 'dyn', 'cresc', 'pedal', 'tuplet', 'chord',
    'note'; match is the regex match for tuplet/chord/note (None
    otherwise); grace is True when the token carried a leading '+'. A
    token that matches no note rule classifies as ('note', None, grace),
    leaving the caller to raise a context-specific error."""
    if tok == "|":
        return "bar", None, False
    if tok.startswith("!"):
        return "dyn", None, False
    if tok in ("cresc", "dim"):
        return "cresc", None, False
    if tok in PEDAL_MARKS:
        return "pedal", None, False
    if METER_RE.match(tok):
        return "meter", None, False
    grace = tok.startswith("+")
    body = tok[1:] if grace else tok
    tm = TUPLET_RE.match(body)
    if tm:
        return "tuplet", tm, grace
    cm = CHORD_RE.match(body)
    if cm:
        return "chord", cm, grace
    return "note", NOTE_RE.match(body), grace


def _map_note_token(tok, fn, state):
    kind, m, grace = _classify(tok)
    pre = "+" if grace else ""
    if kind == "tuplet":
        inner, dur = m.group(1), m.group(2) or ""
        parts = [_map_note_token(t, fn, state) for t in _tokenize(inner)]
        return pre + "{" + " ".join(parts) + "}" + dur
    if kind == "chord":
        inner, dur, marks = m.group(1), m.group(2) or "", m.group(3) or ""
        parts = []
        for t in inner.split():
            nm = NOTE_RE.match(t)
            if not nm:
                raise CompositionError(f"transform: bad chord member '{t}'")
            parts.append(_apply(nm, fn, state, dur=""))
        return pre + "[" + " ".join(parts) + "]" + dur + marks
    if m is None or m.group(1) == "r":
        return tok
    return pre + _apply(m, fn, state, dur=(m.group(4) or ""))


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
        if _classify(tok)[0] in ("bar", "dyn", "cresc", "pedal", "meter"):
            out.append(tok)
            continue
        out.append(_map_note_token(tok, fn, state))
    return " ".join(out)


def shift(frag: str, degrees: int) -> str:
    """Transpose every pitch in the fragment by N diatonic steps.
    Explicit alterations (#, b, n) travel with their scale degree."""
    def fn(letter, acc, octave):
        idx = octave * 7 + LETTERS.index(letter) + degrees
        return LETTERS[idx % 7], acc, idx // 7
    return _transform(frag, fn)


MIRROR_ACC = {"": "", "n": "n", "#": "b", "b": "#", "##": "bb", "bb": "##"}


def invert(frag: str, axis: str = "g4") -> str:
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


# Letter steps that spell a transposition of N semitones (0-11): a minor
# second is one letter, a tritone an augmented fourth, and so on.
_SEMI_STEPS = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 5, 9: 5,
               10: 6, 11: 6}
_ALTER = {-2: "bb", -1: "b", 0: "n", 1: "#", 2: "##"}


def transpose(frag: str, semitones: int, key: str = "C") -> str:
    """Transpose every pitch in the fragment by N semitones, chromatic
    where shift() is diatonic. `key` is the signature the fragment is
    read in (letters without an accidental take it). Results are spelled
    by interval, so up a minor third from B is D rather than C##, and
    carry explicit accidentals (n for natural), so they read the same
    under any key."""
    sig = _resolve_key(key)
    mag = abs(semitones)
    steps = (_SEMI_STEPS[mag % 12] + 7 * (mag // 12)) * (1 if semitones >= 0
                                                          else -1)

    def fn(letter, acc, octave):
        target = 12 * (octave + 1) + _pc(letter, acc, sig) + semitones
        idx = octave * 7 + LETTERS.index(letter) + steps
        nl, no = LETTERS[idx % 7], idx // 7
        alter = target - (12 * (no + 1) + STEP[nl])
        if alter not in _ALTER:
            raise CompositionError(
                f"transpose: {letter}{acc}{octave} by {semitones} cannot be "
                f"spelled on {nl.upper()}")
        return nl, _ALTER[alter], no
    return _transform(frag, fn)


def double(frag: str, degrees: int = 7) -> str:
    """Double every note of the fragment a diatonic interval away: 7 adds
    the octave above, -7 the octave below, -2 a third below, -5 a sixth
    below. An octave keeps the note's accidental, so it is exact; a
    third or a sixth takes the key signature, as a hand playing in thirds
    does, so a chromatic exception is written by hand. Chords double
    every member, tuplet members become chords, and rests, graces,
    marks, and onset anchors pass through. A trilled note cannot be
    doubled."""
    if degrees == 0:
        raise CompositionError("double: degrees must not be 0")
    exact = degrees % 7 == 0
    state = {"oct": 4}

    def members(nm):
        """The note and its double, low to high, octaves written out."""
        letter, acc = nm.group(1), nm.group(2) or ""
        if nm.group(3):
            state["oct"] = int(nm.group(3))
        o = state["oct"]
        idx = o * 7 + LETTERS.index(letter) + degrees
        this = f"{letter}{acc}{o}"
        other = f"{LETTERS[idx % 7]}{acc if exact else ''}{idx // 7}"
        return [other, this] if degrees < 0 else [this, other]

    def chord_of(inner, where):
        names = []
        for t in inner.split():
            nm = NOTE_RE.match(t)
            if not nm or nm.group(1) == "r" or nm.group(4) or nm.group(5):
                raise CompositionError(
                    f"double: bad chord member '{t}' in {where}")
            names += [n for n in members(nm) if n not in names]
        return "[" + " ".join(names) + "]"

    def tuplet_of(tok):
        """A tuplet with each member doubled, nested tuplets included."""
        tm = TUPLET_RE.match(tok)
        parts = []
        for t in _tokenize(tm.group(1)):
            cm, nm = CHORD_RE.match(t), NOTE_RE.match(t)
            if TUPLET_RE.match(t):
                parts.append(tuplet_of(t))
            elif cm:
                parts.append(chord_of(cm.group(1), tok)
                             + (cm.group(2) or "") + (cm.group(3) or ""))
            elif nm and nm.group(1) == "r":
                parts.append(t)
            elif nm:
                parts.append("[" + " ".join(members(nm)) + "]"
                             + (nm.group(4) or "") + (nm.group(5) or ""))
            else:
                raise CompositionError(
                    f"double: bad tuplet member '{t}' in {tok}")
        return "{" + " ".join(parts) + "}" + (tm.group(2) or "")

    out = []
    for tok in _tokenize(frag):
        anchor = ""
        if "@" in tok and not tok.startswith("!"):
            tok, _, at = tok.partition("@")
            anchor = "@" + at
        kind, m, grace = _classify(tok)
        if kind in ("bar", "dyn", "cresc", "pedal", "meter"):
            out.append(tok)
            continue
        if grace:
            nm = NOTE_RE.match(tok[1:])
            if not nm or nm.group(1) == "r":
                raise CompositionError(f"double: bad grace note '{tok}'")
            if nm.group(3):
                state["oct"] = int(nm.group(3))
            out.append(f"+{nm.group(1)}{nm.group(2) or ''}{state['oct']}"
                       f"{nm.group(5) or ''}{anchor}")
            continue
        if kind == "tuplet":
            out.append(tuplet_of(tok) + anchor)
        elif kind == "chord":
            out.append(chord_of(m.group(1), tok) + (m.group(2) or "")
                       + (m.group(3) or "") + anchor)
        elif m is None:
            raise CompositionError(f"double: unrecognized token '{tok}'")
        elif m.group(1) == "r":
            out.append(tok + anchor)
        elif "%" in (m.group(5) or ""):
            raise CompositionError(
                f"double: '{tok}' is trilled, and a trill takes one note")
        else:
            out.append("[" + " ".join(members(m)) + "]" + (m.group(4) or "")
                       + (m.group(5) or "") + anchor)
    return " ".join(out)


Mapped = namedtuple("Mapped", "pitch beats at bar")
Mapped.__doc__ = """A note handed to map_notes(): its MIDI pitch, its length
in beats, its onset in beats from the fragment's start, and its bar,
counted from 0 and advanced by each barline."""


def map_notes(frag: str, fn, key: str = "C") -> str:
    """Rewrite each single note of a fragment through `fn`, string to
    string: the general form of double(), and of the helper a hand
    voicing a tune otherwise writes for itself. `fn` receives a Mapped
    (pitch, beats, at, bar) for every note, tuplet members included, the
    pitch read in `key`; it returns a pitch, a list of pitches (written
    as a chord), an empty list (the note becomes a rest), or None (the
    note stays). Rests, chords, grace notes, marks, durations, dynamics,
    and onset anchors pass through. Every pitch comes back with its
    octave written out, and new pitches carry explicit accidentals, so
    the result reads the same under any signature:

        map_notes(tune, lambda n: [chord_tone_below(n.pitch, "Dm7"),
                                   n.pitch])
    """
    sig = _resolve_key(key)
    state = {"oct": 4, "dur": 1.0}
    where = {"t": 0.0, "bar": 0}

    def octave(nm):
        if nm.group(3):
            state["oct"] = int(nm.group(3))
        return state["oct"]

    def as_written(nm):
        return f"{nm.group(1)}{nm.group(2) or ''}{octave(nm)}"

    def mapped(nm, beats, at, dur, marks):
        written = as_written(nm)
        p = 12 * (state["oct"] + 1) + _pc(nm.group(1), nm.group(2) or "", sig)
        result = fn(Mapped(p, beats, at, where["bar"]))
        if result is None:
            return written + dur + marks
        ps = [result] if isinstance(result, int) else sorted(set(result))
        if not ps:
            return "r" + dur + ("^" if "^" in marks else "")
        if len(ps) > 1 and "%" in marks:
            raise CompositionError(
                f"map_notes: {written} is trilled, and a trill takes one "
                f"note")
        body = " ".join(note_name(q, key) for q in ps)
        return (body if len(ps) == 1 else f"[{body}]") + dur + marks

    def chord(cm):
        members = [NOTE_RE.match(x) for x in cm.group(1).split()]
        if not all(members) or any(x.group(1) == "r" for x in members):
            raise CompositionError(
                f"map_notes: bad chord member in [{cm.group(1)}]")
        return ("[" + " ".join(as_written(x) for x in members) + "]"
                + (cm.group(2) or "") + (cm.group(3) or ""))

    def tuplet(tm, span, at):
        members = _tokenize(tm.group(1))
        each = span / len(members)
        parts = []
        for k, mem in enumerate(members):
            sub, cm, nm = (TUPLET_RE.match(mem), CHORD_RE.match(mem),
                           NOTE_RE.match(mem))
            if sub:
                parts.append(tuplet(sub, each, at + k * each))
            elif cm:
                parts.append(chord(cm))
            elif nm and nm.group(1) == "r":
                parts.append(mem)
            elif nm:
                parts.append(mapped(nm, each, at + k * each, "",
                                    nm.group(5) or ""))
            else:
                raise CompositionError(
                    f"map_notes: bad tuplet member '{mem}'")
        return "{" + " ".join(parts) + "}" + (tm.group(2) or "")

    out = []
    for tok in _tokenize(frag):
        anchor = ""
        if "@" in tok and not tok.startswith("!"):
            tok, _, at = tok.partition("@")
            anchor = "@" + at
            where["t"] = max(where["t"], float(at))
        kind, m, grace = _classify(tok)
        if kind in ("bar", "dyn", "cresc", "pedal", "meter"):
            if kind == "bar":
                where["bar"] += 1
            out.append(tok)
            continue
        if grace:
            nm = NOTE_RE.match(tok[1:])
            if not nm or nm.group(1) == "r":
                raise CompositionError(f"map_notes: bad grace note '{tok}'")
            out.append("+" + as_written(nm) + (nm.group(5) or "") + anchor)
            continue
        if kind == "tuplet":
            if m.group(2):
                state["dur"] = _dur_value(m.group(2))
            out.append(tuplet(m, state["dur"], where["t"]) + anchor)
        elif kind == "chord":
            if m.group(2):
                state["dur"] = _dur_value(m.group(2))
            out.append(chord(m) + anchor)
        elif m is None:
            raise CompositionError(f"map_notes: unrecognized token '{tok}'")
        else:
            if m.group(4):
                state["dur"] = _dur_value(m.group(4))
            if m.group(1) == "r":
                out.append(tok + anchor)
            else:
                out.append(mapped(m, state["dur"], where["t"],
                                  m.group(4) or "", m.group(5) or "")
                           + anchor)
        where["t"] += state["dur"]
    return " ".join(out)


def chord_tone_below(pitch: int, symbol: str, gap: int = 3) -> int:
    """The highest tone of chord `symbol` at least `gap` semitones below
    `pitch`: the inner note a hand adds under a melody note, with
    map_notes()."""
    pcs = {p % 12 for p in chord_pitches(symbol)}
    return next(q for q in range(pitch - gap, pitch - gap - 12, -1)
                if q % 12 in pcs)


def _line(frag: str, key: str) -> list:
    """(onset, pitch, beats) for each note of a fragment, the top note of
    a chord, tuplet members included and tied notes joined; rests and
    grace notes leave no event."""
    sig = _resolve_key(key)
    state = {"oct": 4, "dur": 1.0, "tie": False}
    out, t = [], 0.0

    def pitch(nm):
        if nm.group(3):
            state["oct"] = int(nm.group(3))
        return 12 * (state["oct"] + 1) + _pc(nm.group(1), nm.group(2) or "",
                                              sig)

    def add(at, p, beats, tied):
        last = out[-1] if out else None
        if (state["tie"] and last and last[1] == p
                and abs(last[0] + last[2] - at) < 1e-6):
            out[-1] = (last[0], p, last[2] + beats)
        else:
            out.append((at, p, beats))
        state["tie"] = tied

    def members(body, span, at):
        mems = _tokenize(body)
        each = span / len(mems)
        for k, mem in enumerate(mems):
            a = at + k * each
            tm, cm, nm = (TUPLET_RE.match(mem), CHORD_RE.match(mem),
                          NOTE_RE.match(mem))
            if tm:
                members(tm.group(1), each, a)
            elif cm:
                add(a, max(pitch(NOTE_RE.match(x))
                           for x in cm.group(1).split()),
                    each, "~" in (cm.group(3) or ""))
            elif nm and nm.group(1) != "r":
                add(a, pitch(nm), each, "~" in (nm.group(5) or ""))
            else:
                state["tie"] = False

    for tok in _tokenize(frag):
        if "@" in tok and not tok.startswith("!"):
            tok, _, at = tok.partition("@")
            t = max(t, float(at))
        kind, m, grace = _classify(tok)
        if kind in ("bar", "dyn", "cresc", "pedal", "meter"):
            continue
        if grace:
            nm = NOTE_RE.match(tok[1:])
            if nm:
                pitch(nm)
            continue
        if m is None:
            raise CompositionError(f"unrecognized token '{tok}'")
        if kind == "tuplet":
            if m.group(2):
                state["dur"] = _dur_value(m.group(2))
            members(m.group(1), state["dur"], t)
        elif kind == "chord":
            if m.group(2):
                state["dur"] = _dur_value(m.group(2))
            add(t, max(pitch(NOTE_RE.match(x)) for x in m.group(1).split()),
                state["dur"], "~" in (m.group(3) or ""))
        else:
            if m.group(4):
                state["dur"] = _dur_value(m.group(4))
            if m.group(1) == "r":
                state["tie"] = False
            else:
                add(t, pitch(m), state["dur"], "~" in (m.group(5) or ""))
        t += state["dur"]
    return out


def _shape_match(line: list, motif: list) -> int | None:
    """The transposition in semitones taking `motif` onto `line` when the
    two strike their notes at the same distances apart and every interval
    agrees, else None. Note lengths are not compared: staccato, legato,
    and a performance's releases leave a motif's rhythm as it was."""
    if len(line) != len(motif) or not motif:
        return None
    shift = line[0][1] - motif[0][1]
    for (ta, pa, _da), (tb, pb, _db) in zip(line, motif):
        if (abs((ta - line[0][0]) - (tb - motif[0][0])) > 1e-6
                or pa - pb != shift):
            return None
    return shift


def same_shape(a: str, b: str, key: str = "C") -> bool:
    """Whether two fragments carry the same rhythm and the same intervals,
    one an exact, chromatic transposition of the other, compared on the
    top note of each chord by where each note is struck, so articulation
    and note lengths do not count: the check that a motif was moved
    without being altered."""
    return _shape_match(_line(a, key), _line(b, key)) is not None


def _timed(frag: str, key: str) -> list:
    """Walk a fragment as a voice reads it, with sticky octaves and
    durations and the key signature applied: per token, (token, kind,
    onset, beats, pitches, bar, octave), kind being 'note', 'rest',
    'chord', 'tuplet', 'grace', 'bar', or a mark kind, and octave the
    sticky octave after the token. Graces and marks take no time; an
    onset anchor moves the clock."""
    sig = _resolve_key(key)
    state = {"oct": 4, "dur": 1.0}
    t, bar, out = 0.0, 0, []

    def pitch(nm):
        if nm is None:
            raise CompositionError(f"unreadable pitch in '{tok}'")
        if nm.group(3):
            state["oct"] = int(nm.group(3))
        return 12 * (state["oct"] + 1) + _pc(nm.group(1), nm.group(2) or "",
                                              sig)

    def dur(durtok):
        if durtok:
            state["dur"] = _dur_value(durtok)
        return state["dur"]

    def members(inner):
        """The pitches of a tuplet's members, nested tuplets included."""
        ps = []
        for mem in _tokenize(inner):
            tm, cm, nm = (TUPLET_RE.match(mem), CHORD_RE.match(mem),
                          NOTE_RE.match(mem))
            if tm:
                ps += members(tm.group(1))
            elif cm:
                ps += [pitch(NOTE_RE.match(x)) for x in cm.group(1).split()]
            elif nm is None or nm.group(1) != "r":
                ps.append(pitch(nm))
        return ps

    for tok in _tokenize(frag):
        base, beats, ps = tok, 0.0, []
        if "@" in tok and not tok.startswith("!"):
            base, _, at = tok.partition("@")
            t = max(t, float(at))
        kind, m, grace = _classify(base)
        if kind in ("bar", "dyn", "cresc", "pedal", "meter"):
            pass
        elif grace:
            kind, ps = "grace", [pitch(NOTE_RE.match(base[1:]))]
        elif kind == "tuplet":
            ps = members(m.group(1))
            beats = dur(m.group(2))
        elif kind == "chord":
            ps = [pitch(NOTE_RE.match(x)) for x in m.group(1).split()]
            beats = dur(m.group(2))
        elif m is None:
            raise CompositionError(f"unrecognized token '{tok}'")
        else:
            beats = dur(m.group(4))
            if m.group(1) == "r":
                kind = "rest"
            else:
                ps = [pitch(m)]
        out.append((tok, kind, t, beats, ps, bar, state["oct"]))
        t += beats
        if kind == "bar":
            bar += 1
    return out


def harmonize(frag: str, symbols: str, key: str = "C", voices: int = 3,
              span: int = 12, bass: str | None = None,
              slots: str | float = "bar") -> str:
    """Voice a melody as chords, string to string: each note of `frag`
    becomes the top of a chord of `voices` notes, the others drawn from
    the chord symbol sounding under it (one per bar, or per `slots`
    beats; '.' repeats and '*N' multiplies, as in harmony()) within
    `span` semitones below. The added notes are chosen over the whole
    passage by dynamic programming: no two voices, and no voice against
    `bass` (a fragment of the bass line, which they stay above), move in
    consecutive fifths or octaves; the inner voices move as little as
    they can; each chord keeps its third and avoids doubling. A tied
    note keeps its chord. Rests, graces, chords, tuplets, trilled notes,
    and marks pass through. `key` is the signature the fragment is read
    in, and spells the added notes (with explicit accidentals)."""
    if voices < 2:
        raise CompositionError("harmonize: voices is 2 or more")
    if slots != "bar":
        try:
            per = 0.0 if isinstance(slots, bool) else float(slots)
        except (TypeError, ValueError):
            per = 0.0
        if not per > 0:
            raise CompositionError(
                f'harmonize: slots is "bar" or a positive number of beats '
                f'(got {slots!r})')
        slots = per
    syms = []
    for tok in _tokenize(symbols):
        if tok == "|":
            continue
        if tok == ".":
            if not syms:
                raise CompositionError("harmonize: '.' with no prior chord")
            tok = syms[-1]
        syms.append(tok)
    if not syms:
        raise CompositionError("harmonize: no chord symbols")
    walk = _timed(frag, key)
    lows = [(w[2], w[3], min(w[4])) for w in (_timed(bass, key) if bass
                                               else []) if w[4] and w[3] > 0]

    def bass_at(t):
        for t0, b, p in lows:
            if t0 - 1e-9 <= t < t0 + b - 1e-9:
                return p
        return None

    events = []                    # (walk index, onset, pitch, symbol)
    for i, (tok, kind, t, _b, ps, bar, _o) in enumerate(walk):
        if kind != "note" or "%" in tok:
            continue
        slot = bar if slots == "bar" else int((t + 1e-9) // float(slots))
        if slot >= len(syms):
            raise CompositionError(
                f"harmonize: {len(syms)} chord symbols, but the melody "
                f"reaches slot {slot + 1} (one symbol per "
                f"{'bar' if slots == 'bar' else f'{slots:g} beats'})")
        events.append((i, t, ps[0], syms[slot]))

    options = []
    for i, t, p, sym in events:
        chord, has_bass = _chord_tones(sym, 4, "harmonize")
        core = chord[1:] if has_bass else chord
        pcs = {x % 12 for x in chord}
        third = core[1] % 12 if len(core) > 1 else core[0] % 12
        floor = bass_at(t)
        cands = [x for x in range(p - span, p)
                 if x % 12 in pcs and (floor is None or x > floor)]
        opts = []
        for combo in itertools.combinations(cands, voices - 1):
            cost = 0.0
            held = {x % 12 for x in combo} | {p % 12}
            if third not in held:
                cost += 3
            cost += 2 * (len(combo) + 1 - len(held))
            # a second against the melody grates; between inner voices it
            # is only close
            cost += 4 * (p - combo[-1] < 3) + sum(
                1 for a, b in zip(combo, combo[1:]) if b - a < 3)
            opts.append((combo, cost))
        options.append(opts or [((), 0.0)])

    def lines_cost(prev, cur, t):
        (pc, pp), (cc, cp) = prev, cur
        cost = 0.0
        a = list(pc) + [pp]
        b = list(cc) + [cp]
        pairs = list(zip(a, b)) if len(a) == len(b) else [(pp, cp)]
        b0, b1 = bass_at(t - 1e-6), bass_at(t)
        if b0 is not None and b1 is not None:
            pairs.append((b0, b1))
        for x in range(len(pairs)):
            for y in range(x + 1, len(pairs)):
                (u0, u1), (v0, v1) = pairs[x], pairs[y]
                if u0 != u1 and v0 != v1:
                    iv0, iv1 = (u0 - v0) % 12, (u1 - v1) % 12
                    if iv0 == iv1 and iv0 in (0, 7):
                        cost += 100
        if len(pc) == len(cc):
            cost += 0.5 * sum(abs(x - y) for x, y in zip(pc, cc))
        return cost

    best = []
    for k, ((wi, t, p, _sym), opts) in enumerate(zip(events, options)):
        layer = {}
        prev_ev = events[k - 1] if k else None
        adjacent = (prev_ev is not None
                    and walk[prev_ev[0]][2] + walk[prev_ev[0]][3] >= t - 1e-9)
        tied = (adjacent and "~" in walk[prev_ev[0]][0]
                and prev_ev[2] == p)
        for combo, cost in opts:
            if not best:
                layer[combo] = (cost, None)
                continue
            choices = []
            for pcombo, (pcost, _back) in best[-1].items():
                if tied and pcombo != combo:
                    continue
                move = (lines_cost((pcombo, prev_ev[2]), (combo, p), t)
                        if adjacent else 0.0)
                choices.append((pcost + move + cost, pcombo))
            if choices:
                layer[combo] = min(choices, key=lambda c: c[0])
        if not layer:                      # a tie the chord cannot keep
            layer = {c: (best[-1][c][0], c) for c in best[-1]}
        best.append(layer)
    chosen = {}
    if best:
        combo = min(best[-1], key=lambda c: best[-1][c][0])
        for k in range(len(best) - 1, -1, -1):
            chosen[events[k][0]] = combo
            combo = best[k][combo][1]
    out = []
    for i, (tok, _kind, _t, _b, _ps, _bar, octave) in enumerate(walk):
        combo = chosen.get(i)
        if combo:
            base, at, anchor = tok.partition("@")
            m = NOTE_RE.match(base)
            tok = ("[" + " ".join([note_name(x, key) for x in combo]
                                  + [f"{m.group(1)}{m.group(2) or ''}{octave}"])
                   + "]" + (m.group(4) or "") + (m.group(5) or "") + at
                   + anchor)
        out.append(tok)
    return " ".join(out)


def retro(frag: str) -> str:
    """Reverse the fragment. A grace note travels with the note it
    ornaments, and tuplet members reverse within their tuplet. Sticky
    octaves and durations are written out first, so reversal cannot
    change what any token means. Barlines, dynamics, and ties are not
    permitted inside; strip them and reapply around the result."""
    toks = _tokenize(frag)
    if "|" in toks or any(METER_RE.match(t) for t in toks):
        raise CompositionError(
            "retro: remove barlines and meter changes from the fragment")
    for t in toks:
        if t.startswith("!") or t in ("cresc", "dim") or t in PEDAL_MARKS:
            raise CompositionError(
                "retro: remove dynamics and pedal marks from the fragment "
                "and reapply them around the result")
        if "~" in t:
            raise CompositionError(
                "retro: remove ties from the fragment — a reversed tie "
                "points the wrong way")
    state = {"oct": 4, "dur": "q"}

    def explicit_pitch(nm):
        """The pitch part of a note token with its octave written out."""
        letter, acc = nm.group(1), nm.group(2) or ""
        if nm.group(3):
            state["oct"] = int(nm.group(3))
        if letter == "r":
            return letter
        return letter + acc + str(state["oct"])

    def explicit_dur(durtok):
        if durtok:
            state["dur"] = durtok
        return state["dur"]

    def chord_members(inner, where):
        parts = []
        for t in inner.split():
            nm = NOTE_RE.match(t)
            if not nm or nm.group(1) == "r":
                raise CompositionError(f"retro: bad chord member '{t}' "
                                       f"in {where}")
            parts.append(explicit_pitch(nm))
        return parts

    def reversed_members(inner, tok):
        """A tuplet's members reversed, nested tuplets reversed within."""
        members = []
        for t in _tokenize(inner):
            mc, mt = CHORD_RE.match(t), TUPLET_RE.match(t)
            if mt:
                members.append("{" + " ".join(reversed_members(mt.group(1),
                                                               tok)) + "}")
            elif mc:
                members.append(
                    "[" + " ".join(chord_members(mc.group(1), tok))
                    + "]" + (mc.group(2) or "") + (mc.group(3) or ""))
            else:
                mn = NOTE_RE.match(t)
                if not mn:
                    raise CompositionError(
                        f"retro: bad tuplet member '{t}' in {tok}")
                members.append(explicit_pitch(mn)
                               + (mn.group(4) or "") + (mn.group(5) or ""))
        return list(reversed(members))

    units = []                     # each unit: [grace..., principal]
    graces = []
    for tok in toks:
        if tok.startswith("+"):
            nm = NOTE_RE.match(tok[1:])
            if not nm or nm.group(1) == "r" or nm.group(4):
                raise CompositionError(f"retro: bad grace note '{tok}'")
            graces.append("+" + explicit_pitch(nm) + (nm.group(5) or ""))
            continue
        kind, m, _grace = _classify(tok)
        if kind == "tuplet":
            out = ("{" + " ".join(reversed_members(m.group(1), tok)) + "}"
                   + explicit_dur(m.group(2)))
        elif kind == "chord":
            out = ("[" + " ".join(chord_members(m.group(1), tok)) + "]"
                   + explicit_dur(m.group(2)) + (m.group(3) or ""))
        elif kind == "note" and m is not None:
            out = (explicit_pitch(m) + explicit_dur(m.group(4))
                   + (m.group(5) or ""))
        else:
            raise CompositionError(f"retro: unrecognized token '{tok}'")
        units.append(graces + [out])
        graces = []
    if graces:
        raise CompositionError(
            "retro: a trailing grace note has no note to ornament")
    return " ".join(t for unit in reversed(units) for t in unit)


_DUR_VALUE_TO_TOKEN = {}
for _sym, _val in DUR.items():
    _DUR_VALUE_TO_TOKEN[round(_val, 6)] = _sym
    _DUR_VALUE_TO_TOKEN[round(_val * 1.5, 6)] = _sym + "."
    _DUR_VALUE_TO_TOKEN.setdefault(round(_val * 1.75, 6), _sym + "..")


def stretch(frag: str, factor: float) -> str:
    """Scale every duration by `factor`: any positive number, with 2
    augmenting and 0.5 diminishing. Each resulting duration must be
    spellable as one of w h q e s t x, with up to two dots; a factor that
    lands a note on a value that cannot be written is rejected, naming
    the offending note and its would-be duration."""
    if factor <= 0:
        raise CompositionError("stretch: factor must be a positive number")

    def stretch_dur(durtok, tok):
        if not durtok:
            return durtok
        new = round(_dur_value(durtok) * factor, 6)
        name = _DUR_VALUE_TO_TOKEN.get(new)
        if name is None:
            raise CompositionError(
                f"stretch by {factor}: '{tok}' would become {new} beats, "
                f"which is not spellable as w/h/q/e/s/t/x (dotted at most "
                f"twice) — choose a factor whose result lands on a real "
                f"duration")
        return name

    out = []
    for tok in _tokenize(frag):
        kind, m, grace = _classify(tok)
        if kind in ("bar", "dyn", "cresc", "pedal", "meter"):
            out.append(tok)
            continue
        pre = "+" if grace else ""
        if kind == "tuplet":
            out.append(pre + "{" + m.group(1) + "}"
                       + stretch_dur(m.group(2) or "", tok))
        elif kind == "chord":
            nd = stretch_dur(m.group(2) or "", tok)
            out.append(pre + "[" + m.group(1) + "]" + nd + (m.group(3) or ""))
        elif m is not None:
            nd = stretch_dur(m.group(4) or "", tok)
            out.append(pre + (m.group(1) + (m.group(2) or "")
                              + (m.group(3) or "") + nd + (m.group(5) or "")))
        else:
            out.append(tok)
    return " ".join(out)


def rebar(frag: str, beats_per_bar: float) -> str:
    """Insert barlines every `beats_per_bar` beats, honoring sticky
    durations, dots, tuplets, chords, graces, and dynamics tokens; a
    meter change (M:3/4) at a bar start sets the bar length from there.
    Errors if a token would cross a barline or the fragment does not
    end on one."""
    toks = _tokenize(frag)
    if "|" in toks:
        raise CompositionError("rebar: fragment already contains barlines")

    def dur_of(durtok, state):
        if durtok:
            state["dur"] = _dur_value(durtok)
        return state["dur"]

    state = {"dur": 1.0}
    out = []
    filled = 0.0
    for tok in toks:
        beats = 0.0
        kind, m, grace = _classify(tok)
        if kind == "meter":
            if filled > 1e-9:
                raise CompositionError(
                    f"rebar: meter change '{tok}' falls inside a bar")
            beats_per_bar = _meter_beats(tok[2:])
            out.append(tok)
            continue
        if kind in ("dyn", "cresc", "pedal") or grace:
            pass                      # marks and grace notes carry no time
        elif kind == "tuplet":
            beats = dur_of(m.group(2), state)
        elif kind == "chord":
            beats = dur_of(m.group(2), state)
        elif kind == "note" and m is not None:
            beats = dur_of(m.group(4), state)
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
    """One event of a voice: pitches struck together (none for a rest)
    for `beats` beats. `gate` is the sounding fraction of the written
    length; `hold` marks a fermata, which stretches time under the note;
    `trill` marks the notes a trill expands into; `marks` keeps the
    written articulation marks for engraving; `spell` keeps each pitch's
    written (letter, alteration, octave), so the engraving shows E-flat
    where E-flat was written; `tup` is the path of tuplets enclosing the
    note, outermost first, each (group id, members, span in beats);
    `vels`, when given, is each pitch's own velocity in the order of
    `pitches`, for a chord struck unevenly, `vel` then being the
    loudest."""
    __slots__ = ("pitches", "beats", "vel", "gate", "tie", "grace",
                 "roll", "trill", "hold", "marks", "spell", "tup", "vels")

    def __init__(self, pitches: list[int], beats: float, vel: int,
                 gate: float = 0.92, tie: bool = False, grace: bool = False,
                 roll: bool = False, trill: bool = False, hold: bool = False,
                 marks: str = "", spell: list | None = None,
                 tup: tuple = (), vels: list | None = None):
        self.pitches = pitches
        self.beats = beats
        self.vel = vel
        self.gate = gate
        self.tie = tie
        self.grace = grace
        self.roll = roll
        self.trill = trill
        self.hold = hold
        self.marks = marks
        self.spell = spell
        self.tup = tup
        self.vels = vels


def _suggest(raw: str) -> str:
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
    if raw.lower().rstrip(".") in ("pedal", "ped", "sus", "sustain", "*"):
        hints.append("pedal marks are 'ped' (press or change) and 'lift'")
    if "..." in raw:
        hints.append("a duration takes at most two dots")
    if raw.endswith("*") or re.search(r"\*\D", raw):
        hints.append("repeat with a count: 'c4e*4' or '(c4e d4e)*2'")
    return ("  hint: " + "; ".join(hints)) if hints else ""


class Voice:
    def __init__(self, name: str, song: "Song", vel: int = 50,
                 octave: int = 4, key: str | None = None, program: int = 0,
                 channel: int = 0, bpb: float | None = None,
                 absolute: bool = False, drums: bool = False):
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
        self.absolute = absolute
        self.drums = drums
        self.section = None        # set by the Section that owns the voice
        self.pedal_marks = []      # (beat, "ped" | "lift") from bars()
        self.dyn_marks = {}        # note index -> dynamic, for engraving
        self.hairpins = {}         # note index -> "<" or ">"
        self._spelled = []         # written spellings awaiting their Note
        self.barlines = []         # beat of each barline written in bars()
        self._bars_done = 0        # full bars written, after any pickup
        self._pickup_first = False  # the voice opened with a pickup bar

    def _bar_length(self, number: int) -> float:
        """Beats in bar `number` (1 = the first full bar) under the
        section's meters."""
        if self.section is not None:
            return self.section._meter_at(number)[0]
        return self.bpb

    def _declare_meter(self, bar: int, time: str) -> None:
        """Record a meter change a voice writes inline (M:3/4) with its
        section, where every voice shares it; voices may repeat a change
        but not contradict one."""
        if self.section is None:
            raise CompositionError(
                f"voice '{self.name}': a meter change needs a section")
        _meter_beats(time)
        have = self.section.meters.get(bar)
        if have is not None and have != time:
            raise CompositionError(
                f"voice '{self.name}' changes the meter to {time} at bar "
                f"{bar}, where its section already changes to {have}")
        self.section.meters[bar] = time
        self.song._dirty()

    def absolute_onsets(self, on: bool = True) -> "Voice":
        """Opt this voice into absolute-onset anchors. A note may then
        carry '@beat' (c5e@3) to place its onset at an exact beat from
        the voice's start: any gap is filled with a rest, and an onset
        that earlier material has already run past is an error rather
        than a silent drift. Sticky sequential timing stays the default;
        reach for this on long odd-meter lines where a fraction of a
        beat accumulates into a wrong bar."""
        self.absolute = on
        return self

    def bars(self, text: str) -> "Voice":
        self.song._dirty()
        beats_in_bar = 0.0
        first_bar = not self._started
        bar_tokens = []
        for raw in _tokenize(text):
            if raw == "|":
                number = self._bars_done + 1
                want = self._bar_length(number)
                pickup = bool(first_bar and self.song.pickup and abs(
                    beats_in_bar - self.song.pickup) <= 1e-6)
                if pickup:
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
                        f"voice '{self.name}' bar {number}: has "
                        f"{beats_in_bar} beats, expected {want} — {how}."
                        f"{hint}\n    bar was: {' '.join(bar_tokens)}")
                if pickup:
                    self._pickup_first = True
                else:
                    self._bars_done += 1
                self.barlines.append(self.total_beats())
                beats_in_bar = 0.0
                bar_tokens = []
                first_bar = False
                self._started = True
                continue
            bar_tokens.append(raw)
            if METER_RE.match(raw):
                if beats_in_bar > 1e-6:
                    raise CompositionError(
                        f"voice '{self.name}': the meter change '{raw}' "
                        f"must open a bar — put it after the barline")
                self._declare_meter(self._bars_done + 1, raw[2:])
                continue
            if raw in PEDAL_MARKS:
                self.pedal_marks.append((self.total_beats(), raw))
                continue
            if "@" in raw and not (raw.startswith("!")
                                   or raw in ("cresc", "dim")):
                base, _, ostr = raw.partition("@")
                if not self.absolute:
                    raise CompositionError(
                        f"voice '{self.name}': '@' onset anchors require "
                        f"absolute mode — call voice.absolute_onsets() first")
                try:
                    onset = float(ostr)
                except ValueError:
                    raise CompositionError(
                        f"voice '{self.name}': bad onset anchor in '{raw}' "
                        f"(write 'c5e@3', a beat number after '@')")
                cur = self.total_beats()
                gap = round(onset - cur, 6)
                if gap < -1e-6:
                    raise CompositionError(
                        f"voice '{self.name}': onset @{onset:g} is before the "
                        f"current position ({cur:g} beats) — earlier material "
                        f"drifted past it; check the durations")
                if gap > 1e-6:
                    self._fill_gap(gap, cur, onset)
                    beats_in_bar += gap
                raw = base
            if raw.startswith("!"):
                if raw[1:] not in DYN:
                    raise CompositionError(
                        f"unknown dynamic '{raw}' "
                        f"(use !ppp !pp !p !mp !mf !f !ff !fff)")
                self._apply_dynamic(self.song.levels[raw[1:]])
                self.dyn_marks[len(self.notes)] = raw[1:]
                continue
            if raw in ("cresc", "dim"):
                if self._cresc_from is not None:
                    raise CompositionError(
                        f"voice '{self.name}': '{raw}' while an earlier "
                        f"cresc/dim is still open — give the first one "
                        f"its target dynamic (!ppp..!fff) first")
                self._cresc_from = (len(self.notes), self._vel)
                self.hairpins[len(self.notes)] = "<" if raw == "cresc" else ">"
                continue
            if raw.startswith("+"):
                m = NOTE_RE.match(raw[1:])
                if not m or m.group(1) == "r":
                    raise CompositionError(f"bad grace note '{raw}'")
                if m.group(4):
                    raise CompositionError(
                        f"grace note '{raw}' must not carry a duration — "
                        f"a grace is a fixed flick before the next note")
                self._spelled = []
                self.notes.append(Note([self._pitch(m)], 0.0,
                                       max(20, self._vel - 8), grace=True,
                                       spell=self._take_spell()))
                # a mark written before a grace belongs to the note it
                # ornaments
                self._shift_marks(len(self.notes) - 1)
                continue
            self._spelled = []
            beats_in_bar += self._token(raw)
        if beats_in_bar > 1e-6:
            raise CompositionError(
                f"voice '{self.name}': trailing partial bar "
                f"({beats_in_bar} beats) — end on a barline '|'")
        self._check_ties()
        return self

    def _shift_marks(self, k: int) -> None:
        """Move the dynamics and hairpins keyed at note index k or later
        one note on, past a note inserted at k."""
        for marks in (self.dyn_marks, self.hairpins):
            for idx in sorted((i for i in marks if i >= k), reverse=True):
                marks[idx + 1] = marks.pop(idx)

    def _fill_gap(self, gap: float, cur: float, onset: float) -> None:
        """Fill the gap before an onset anchor with a rest, ahead of any
        graces written for the anchored note, so they stay with it. The
        pedal marks, dynamics, and hairpins written for that note move
        past the rest to it."""
        k = len(self.notes)
        while k and self.notes[k - 1].grace:
            k -= 1
        self.notes.insert(k, Note([], gap, 0))
        self._shift_marks(k)
        if self._cresc_from is not None and self._cresc_from[0] >= k:
            self._cresc_from = (self._cresc_from[0] + 1, self._cresc_from[1])
        self.pedal_marks = [(onset if abs(b - cur) < 1e-9 else b, kind)
                            for b, kind in self.pedal_marks]

    def _check_ties(self) -> None:
        """Validate that each tie is followed by the same pitch. A tie on
        the voice's current last sounding note is left pending: at parse
        time it may still resolve in a later bars() call, and at render
        time it is laissez vibrer. Run at the end of every bars() so a
        mismatch surfaces at parse time, not deferred to render."""
        body = [n for n in self.notes if not n.grace]
        for i, n in enumerate(body):
            if n.tie and n.pitches and i + 1 < len(body):
                if set(body[i + 1].pitches) != set(n.pitches):
                    raise CompositionError(
                        f"voice '{self.name}': tie on MIDI {n.pitches} is "
                        f"not followed by the same pitch — remove '~' or "
                        f"repeat the note")

    def _apply_dynamic(self, target):
        if self._cresc_from is not None:
            i0, v0 = self._cresc_from
            span = self.notes[i0:]
            # Each note takes the level the ramp reaches where it ends, so
            # the ramp follows time, not the note count (a trill does not
            # swallow it); a grace takes the level of the note it
            # ornaments. The ramp replaces the level each note was entered
            # at and keeps its offset from it (an accent, a trill's
            # shading, a grace's lift).
            total = sum(n.beats for n in span if not n.grace) or 1.0
            ends, t = [], 0.0
            for n in span:
                if not n.grace:
                    t += n.beats
                ends.append(None if n.grace else t)
            nxt = total
            for k in range(len(ends) - 1, -1, -1):
                if ends[k] is None:
                    ends[k] = nxt
                else:
                    nxt = ends[k]
            for n, end in zip(span, ends):
                if n.pitches:
                    level = v0 + (target - v0) * end / total
                    n.vel = max(1, min(127, int(level + n.vel - v0)))
            self._cresc_from = None
        self._vel = target

    def _token(self, raw: str) -> float:
        if self.drums:
            return self._drum(raw)
        kind, match, _grace = _classify(raw)
        tm = match if kind == "tuplet" else None
        if tm:
            span = self._beats(tm.group(2))
            self._tuplet(tm.group(1), span, raw, ())
            return span
        m = match if kind == "chord" else None
        if m:
            inner, durtok, marks = m.groups()
            pitches = []
            for t in inner.split():
                nm = NOTE_RE.match(t)
                if not nm or nm.group(1) == "r":
                    raise CompositionError(f"bad chord member '{t}' in {raw}")
                if nm.group(4):
                    raise CompositionError(
                        f"chord member '{t}' in {raw} must not carry a "
                        f"duration — write it once after the ']': "
                        f"[c4 e4]{nm.group(4)}")
                if nm.group(5):
                    raise CompositionError(
                        f"chord member '{t}' in {raw} must not carry "
                        f"marks — put them after the ']' and duration: "
                        f"[c4 e4]q{nm.group(5)}")
                pitches.append(self._pitch(nm))
            beats = self._beats(durtok)
            self._push(pitches, beats, marks or "")
            return beats
        m = match if kind == "note" else None
        if not m:
            raise CompositionError(
                f"voice '{self.name}': unrecognized token '{raw}'."
                + _suggest(raw))
        letter = m.group(1)
        beats = self._beats(m.group(4))
        if letter == "r":
            self.notes.append(Note([], beats, 0,
                                   hold="^" in (m.group(5) or "")))
        else:
            self._push([self._pitch(m)], beats, m.group(5) or "")
        return beats

    def _tuplet(self, inner: str, span: float, raw: str, path: tuple) -> None:
        """Divide `span` beats equally among a tuplet's members: notes,
        rests, chords, or tuplets of their own ({c4 {d4 e4 f4} g4}q),
        which divide their member's share in turn. Each Note keeps the
        path of groups enclosing it, for engraving."""
        members = _tokenize(inner)
        if not members:
            raise CompositionError(f"empty tuplet '{raw}'")
        each = span / len(members)
        path = path + ((next(_TUPLET_IDS), len(members), span),)
        for t in members:
            tm = TUPLET_RE.match(t)
            if tm:
                if tm.group(2):
                    raise CompositionError(
                        f"nested tuplet '{t}' in {raw} must not carry a "
                        f"duration — it takes its member's share")
                self._tuplet(tm.group(1), each, raw, path)
                continue
            cm = CHORD_RE.match(t)
            if cm:
                if cm.group(2):
                    raise CompositionError(
                        f"tuplet member '{t}' must not carry a "
                        f"duration — the span divides equally")
                if (cm.group(3) or "").replace("~", ""):
                    raise CompositionError(
                        f"tuplet member '{t}' in {raw}: only a tie "
                        f"'~' may mark a tuplet member")
                pitches = []
                for ct in cm.group(1).split():
                    cn = NOTE_RE.match(ct)
                    if not cn or cn.group(1) == "r":
                        raise CompositionError(
                            f"bad chord member '{ct}' in tuplet {raw}")
                    if cn.group(4) or cn.group(5):
                        raise CompositionError(
                            f"chord member '{ct}' in tuplet {raw} "
                            f"must not carry a duration or marks")
                    pitches.append(self._pitch(cn))
                self.notes.append(Note(pitches, each, self._vel, gate=0.9,
                                       tie="~" in (cm.group(3) or ""),
                                       spell=self._take_spell(), tup=path))
                continue
            nm = NOTE_RE.match(t)
            if not nm:
                raise CompositionError(
                    f"bad tuplet member '{t}' in {raw} (no duration "
                    f"letters inside tuplets)")
            if nm.group(4):
                raise CompositionError(
                    f"tuplet member '{t}' must not carry a duration — "
                    f"the span divides equally")
            if (nm.group(5) or "").replace("~", ""):
                raise CompositionError(
                    f"tuplet member '{t}' in {raw}: only a tie '~' "
                    f"may mark a tuplet member")
            if nm.group(1) == "r":
                self.notes.append(Note([], each, 0, tup=path))
            else:
                self.notes.append(Note([self._pitch(nm)], each, self._vel,
                                       gate=0.9,
                                       tie="~" in (nm.group(5) or ""),
                                       spell=self._take_spell(), tup=path))

    def _take_spell(self):
        """The written spellings gathered since the last Note, handed
        over to the Note being made."""
        spelled, self._spelled = self._spelled, []
        return spelled or None

    def _pitch(self, m):
        letter, acc, octv = m.group(1), m.group(2), m.group(3)
        if octv:
            self._oct = int(octv)
        p = 12 * (self._oct + 1) + _pc(letter, acc, self.key)
        self._spelled.append((letter, _pc(letter, acc, self.key)
                              - STEP[letter], self._oct))
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
            self._dur = _dur_value(durtok)
        return self._dur

    def _push(self, pitches, beats, marks):
        spell = self._take_spell()
        vel = self._vel + (12 if ">" in marks else 0)
        gate = 0.92
        if "'" in marks:
            gate = 0.45
        if "_" in marks:
            gate = 1.04
        hold = "^" in marks        # a fermata: time stretches under it
        if hold:
            gate = 1.0
        if "%" in marks:
            if len(pitches) != 1:
                raise CompositionError("trill '%' works on single notes")
            unit = self.song.trill_rate
            k = int(beats / unit + 1e-9)
            if k < 3:
                raise CompositionError(
                    f"trill '%' on a {beats}-beat note at "
                    f"trill_rate={unit}: too short to alternate — "
                    f"lengthen the note or lower Song(trill_rate=)")
            if k % 2 == 0:
                k -= 1          # alternation ends upper → main, no stutter
            main = pitches[0]
            upper = self._diatonic_upper(main)
            if upper > self.song.pitch_hi:
                raise CompositionError(
                    f"voice '{self.name}': trill on MIDI {main} alternates "
                    f"with MIDI {upper}, outside the instrument range "
                    f"{self.song.pitch_lo}-{self.song.pitch_hi}")
            main_sp = up_sp = None
            if spell:                   # the neighbor is the next letter up
                letter, _alter, octv = spell[0]
                idx = LETTERS.index(letter) + 1
                nl, no = LETTERS[idx % 7], octv + idx // 7
                main_sp = spell
                up_sp = [(nl, upper - 12 * (no + 1) - STEP[nl], no)]
            for i in range(k - 1):
                self.notes.append(Note([main if i % 2 == 0 else upper],
                                       unit, max(20, vel - 6), gate=0.9,
                                       trill=True,
                                       spell=main_sp if i % 2 == 0 else up_sp))
            rem = beats - (k - 1) * unit
            self.notes.append(Note([main], rem, vel, gate, tie="~" in marks,
                                   trill=True, hold=hold, marks=marks,
                                   spell=main_sp))
            return
        self.notes.append(Note(pitches, beats, min(127, vel), gate,
                               tie="~" in marks, roll="&" in marks,
                               hold=hold, marks=marks, spell=spell))

    # ── percussion (channel 10) ──────────────────────────
    def _drum(self, raw: str) -> float:
        """Parse one token of a drum voice: a rest, a drum name, or a
        stack. A duration letter and marks attach to the name; sticky
        durations carry as in melodic notation."""
        m = re.match(r"^r(" + DUR_RX + r")?$", raw)
        if m:
            beats = self._beats(m.group(1))
            self.notes.append(Note([], beats, 0))
            return beats
        if raw.startswith("["):
            cm = re.match(r"^\[([^\]]+)\](" + DUR_RX + r")?([" + MARKS
                          + r"]*)$", raw)
            if not cm:
                raise CompositionError(
                    f"voice '{self.name}': bad drum stack '{raw}'")
            pitches = [self._drum_pitch(nm) for nm in cm.group(1).split()]
            beats = self._beats(cm.group(2))
            self._push_drum(pitches, beats, cm.group(3) or "")
            return beats
        for nm in _DRUM_NAMES:
            if raw.startswith(nm):
                rest = re.match(r"^(" + DUR_RX + r")?([" + MARKS + r"]*)$",
                                raw[len(nm):])
                if rest:
                    beats = self._beats(rest.group(1))
                    self._push_drum([DRUMS[nm]], beats, rest.group(2) or "")
                    return beats
        raise CompositionError(
            f"voice '{self.name}': unknown drum token '{raw}' — names are "
            f"{' '.join(sorted(set(DRUMS)))}, attached to a duration, e.g. "
            f"'bde hh sn hh' or '[bd hh]q'")

    def _drum_pitch(self, name: str) -> int:
        if name not in DRUMS:
            raise CompositionError(
                f"voice '{self.name}': unknown drum '{name}' in a stack — "
                f"names are {' '.join(sorted(set(DRUMS)))}")
        return DRUMS[name]

    def _push_drum(self, pitches, beats, marks) -> None:
        vel = self._vel + (14 if ">" in marks else 0)
        self.notes.append(Note(pitches, beats, min(127, max(1, vel)),
                               gate=0.5, marks=marks))

    # ── harmony ──────────────────────────────────────────
    def harmony(self, symbols: str, style: str = "block", slots: str = "bar",
                octave: int = 3, voicing: str = "plain",
                avoid: "Voice | None" = None, pattern: str | None = None,
                unit: float = 0.5) -> "Voice":
        """Render chord symbols as an accompaniment figure, one symbol
        per `slots`: "bar", "half", or a number of beats. `octave`
        places the chord roots and is independent of the octave the
        voice uses for melodic input. `pattern`, in place of a style,
        figures each chord by indices into its tone ladder (the chord's
        tones stacked up by octaves, a slash bass at index 0): "0 2 4 5
        4 2" steps through the ladder `unit` beats at a time (1/3 for
        triplet eighths), repeating to fill each slot; "r" rests and
        "0+4" strikes two ladder tones together. A step may carry its
        own length after a colon, so a pattern can have a rhythm: the
        habanera is "0:e. 4:s 2+3:e 2+3:e". `avoid` names another
        Voice: chord tones that would double its pitch classes on a
        shared onset are dropped, and single figure tones that would
        collide at the exact unison move down an octave. When the song
        defines a pickup and this voice is still empty, the pickup rest
        is inserted automatically; it gives way when the voices written
        by hand open on a downbeat, whichever is written first. Symbols
        repeat with '*': "Am*4"."""
        self.song._dirty()
        steps = None if pattern is None else self._parse_pattern(pattern)
        if unit <= 0:
            raise CompositionError("harmony: unit must be a positive number "
                                   "of beats")
        if self.song.pickup and not self.notes:
            written = [v for v in (self.section.voices if self.section
                                   else ())
                       if v is not self and v.notes]
            if not written or any(v._anacrusis() for v in written):
                # marked, so it can yield to voices written later
                self.notes.append(Note([], self.song.pickup, 0,
                                       marks="pickup"))
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
        if (isinstance(slots, (int, float)) and not isinstance(slots, bool)
                and slots > 0):
            def slot_at(_t):
                return float(slots)
        elif slots in ("bar", "half"):
            anac = self.song.pickup if (
                self._pickup_first or (self.notes
                                       and self.notes[0].marks == "pickup")
            ) else 0.0

            def slot_at(t):
                """The rest of the bar (or half bar) that beat t is in,
                under the section's meters."""
                pos, number = anac, 1
                while True:
                    beats = self._bar_length(number)
                    if t < pos + beats - 1e-9:
                        break
                    pos, number = pos + beats, number + 1
                if slots == "half" and t < pos + beats / 2 - 1e-9:
                    return pos + beats / 2 - t
                return pos + beats - t
        else:
            raise CompositionError(
                f'harmony: slots is "bar", "half", or a positive number of '
                f'beats (got {slots!r})')
        prev_sym = None
        prev_voicing = None
        t0 = self.total_beats()
        for sym in _tokenize(symbols):
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
            slot_beats = slot_at(t0)
            if steps is not None:
                self._pattern(tones, has_bass, steps, unit, slot_beats, t0,
                              avoid_map)
            else:
                self._figure(tones, style, slot_beats, t0, avoid_map)
            t0 += slot_beats
        return self

    @staticmethod
    def _parse_pattern(pattern: str) -> list:
        """[(ladder indices, or None for a rest; beats, or None to take
        `unit`)] for each step: '0', '0+4', or 'r', with an optional
        ':' and a duration, as in '0:e.' or 'r:s'."""
        steps = []
        for tok in pattern.split():
            body, colon, dur = tok.partition(":")
            beats = None
            if colon:
                if not re.fullmatch(DUR_RX, dur):
                    raise CompositionError(
                        f"harmony: bad pattern step {tok!r} — a length "
                        f"follows the colon, like '0:e.' or 'r:s'")
                beats = _dur_value(dur)
            if body == "r":
                steps.append((None, beats))
                continue
            try:
                idx = [int(x) for x in body.split("+")]
            except ValueError:
                idx = [-1]
            if min(idx) < 0:
                raise CompositionError(
                    f"harmony: bad pattern step {tok!r} — write ladder "
                    f"indices like '0 2 4 2', stacks like '0+4', or 'r', "
                    f"each with an optional length like '0:e.'")
            steps.append((idx, beats))
        if not steps:
            raise CompositionError("harmony: the pattern is empty")
        return steps

    def _pattern(self, tones, has_bass, steps, unit, beats, t0, avoid_map):
        """Figure one chord by a parsed pattern over its tone ladder,
        cycling the steps until the slot is exactly full."""
        bass = [tones[0]] if has_bass else []
        core = tones[1:] if has_bass else list(tones)
        ladder = bass + sorted(p + 12 * k for k in range(5) for p in core)
        if all(d is None for _s, d in steps):
            count = beats / unit
            if int(round(count)) < 1 or abs(count - round(count)) > 1e-6:
                raise CompositionError(
                    f"harmony: a pattern unit of {unit:g} beats does not "
                    f"divide a {beats:g}-beat slot")
        t, i = 0.0, 0
        while t < beats - 1e-6:
            step, d = steps[i % len(steps)]
            d = d or unit
            if t + d > beats + 1e-6:
                cycle = sum(x or unit for _s, x in steps)
                raise CompositionError(
                    f"harmony: the pattern's steps overrun a {beats:g}-beat "
                    f"slot ({t:g} beats in, the next step is {d:g}); one "
                    f"cycle of the pattern is {cycle:g} beats")
            if step is None:
                self.notes.append(Note([], d, 0))
            else:
                if max(step) >= len(ladder):
                    raise CompositionError(
                        f"harmony: pattern index {max(step)} is past the "
                        f"chord's {len(ladder)}-tone ladder")
                vel = self._vel if i == 0 else max(20, self._vel - 6)
                self._emit([ladder[j] for j in step], d, vel, t, t0,
                           avoid_map)
            t += d
            i += 1

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
        for p in pitches:
            if not self.song.pitch_lo <= p <= self.song.pitch_hi:
                raise CompositionError(
                    f"voice '{self.name}': harmony figure reaches MIDI "
                    f"{p}, outside the instrument range "
                    f"{self.song.pitch_lo}-{self.song.pitch_hi} — "
                    f"adjust harmony(octave=)")
        self.notes.append(Note(pitches, beats, vel, gate))

    def _lead(self, prev_upper, upper):
        if not prev_upper or not upper:
            return upper
        center = sum(prev_upper) / len(prev_upper)
        out = []
        for t in upper:
            best = min((t + 12 * k for k in (-1, 0, 1)),
                       key=lambda x: abs(x - center))
            out.append(max(self.song.pitch_lo,
                           min(self.song.pitch_hi, best)))
        return sorted(out)

    def _chord_pitches(self, sym: str, octave: int) -> tuple[list[int], bool]:
        return _chord_tones(sym, octave, "harmony")

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
        elif style in ("alberti", "arp"):
            if style == "alberti":
                third = tones[1] if len(tones) > 1 else root + 4
                fifth = tones[2] if len(tones) > 2 else root + 7
                seq = [root, fifth, third, fifth]
            else:
                seq = tones + [root + 12]
            n = int(beats * 2 + 1e-9)
            for i in range(n):
                self._emit([seq[i % len(seq)]], 0.5, max(20, v - 6),
                           i * 0.5, t0, avoid_map)
            if beats - n * 0.5 > 1e-6:      # a slot of no whole eighths
                self.notes.append(Note([], beats - n * 0.5, 0))
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

    def _anacrusis(self) -> float:
        """Beats of pickup before this voice's first downbeat (0.0 when
        it opens on one), judged from its length."""
        if self.section is not None:
            return self.section._anacrusis_of(self.total_beats())
        return _pickup_of(self.total_beats(), self.song.pickup, self.bpb)

    def _line(self) -> list:
        """(onset, top pitch, beats) for each struck note or chord, tied
        notes joined; grace notes and rests leave no event."""
        out, t, tied = [], 0.0, False
        for n in self.notes:
            if n.grace:
                continue
            if n.pitches:
                top = max(n.pitches)
                last = out[-1] if out else None
                if (tied and last and last[1] == top
                        and abs(last[0] + last[2] - t) < 1e-6):
                    out[-1] = (last[0], top, last[2] + n.beats)
                else:
                    out.append((round(t, 6), top, n.beats))
                tied = n.tie
            else:
                tied = False
            t += n.beats
        return out

    def pitch_metrics(self) -> dict:
        """Pitch-content statistics from the parsed notes: a 12-bin
        pitch-class histogram, the out-of-key rate against the voice's
        key signature, the melodic interval distribution (signed
        semitones between the tops of consecutive sounding notes), mean
        bar-to-bar pitch-class self-similarity, and the grace-note
        count. Lets an agent assert on the content it wrote, graces
        included: a grace carries no duration and so vanishes without a
        trace if dropped, which this count makes visible."""
        if self.drums:
            return {"grace": sum(1 for n in self.notes if n.grace),
                    "drum": True}
        sounding = [n for n in self.notes if n.pitches and not n.grace]
        pcs = [0] * 12
        for n in sounding:
            for p in n.pitches:
                pcs[p % 12] += 1
        total_p = sum(pcs)
        scale = {p % 12 for p in scale_pitches(self.key)}
        out = sum(c for pc, c in enumerate(pcs) if pc not in scale)
        tops = [max(n.pitches) for n in sounding]
        intervals = {}
        for a, b in zip(tops, tops[1:]):
            intervals[b - a] = intervals.get(b - a, 0) + 1
        bar_of = (self.section._bar_index(self.total_beats())
                  if self.section is not None else None)
        anac = self._anacrusis()       # a pickup is bar 0, its own bar
        bar_pcs = {}
        t = 0.0
        for n in self.notes:
            if n.grace:
                continue
            if n.pitches:
                bar = (bar_of(t) if bar_of else
                       int((t - anac + 1e-9) // self.bpb) + (1 if anac else 0))
                bar_pcs.setdefault(bar, set()).update(
                    p % 12 for p in n.pitches)
            t += n.beats
        bars = ([bar_pcs.get(i, set()) for i in range(max(bar_pcs) + 1)]
                if bar_pcs else [])
        sims = [len(a & b) / len(a | b) for a, b in zip(bars, bars[1:]) if a | b]
        return {
            "grace": sum(1 for n in self.notes if n.grace),
            "pitch_classes": pcs,
            "out_of_key_rate": round(out / total_p, 3) if total_p else 0.0,
            "intervals": {str(k): v for k, v in sorted(intervals.items())},
            "self_similarity": round(sum(sims) / len(sims), 3) if sims else 0.0,
        }


class Section:
    def __init__(self, name: str, song: "Song", key: str | None = None,
                 time: str | None = None):
        self.name = name
        self.song = song
        self.key = key
        self.bpb = _meter_beats(time) if time else song.beats_per_bar
        self.time_sig = time or song.time_sig
        self.meters = {}              # bar number -> time signature
        self.voices = []
        self.pedal_mode = None
        self.soft_pedal = False
        self.rubato_depth = 0.0
        self.rubato_phrase = 2
        self.rubato_shape = "arch"
        self.swing_amount = None      # None: the song's swing applies
        self.swing_unit = None

    def voice(self, name: str, vel: int = 50, octave: int = 4,
              program: int = 0, channel: int = 0,
              absolute: bool = False) -> Voice:
        v = Voice(f"{self.name}.{name}", self.song, vel, octave,
                  key=self.key, program=program, channel=channel,
                  bpb=self.bpb, absolute=absolute)
        v.section = self
        self.voices.append(v)
        self.song._dirty()
        return v

    def drums(self, name: str = "kit", vel: int = 70) -> Voice:
        """A General MIDI percussion voice on channel 10 (the drum
        channel). Write it with drum names in place of pitches: bd sn hh
        ho lt mt ht cr rd cb and more (see DRUMS), each carrying a
        duration and sticky like any note, e.g.
        bars("bde hh sn hh | bd hh sn hh |"). Stacks play a kick and
        hat together, [bd hh]q, and '>' accents a hit."""
        v = Voice(f"{self.name}.{name}", self.song, vel,
                  channel=9, bpb=self.bpb, drums=True)
        v.section = self
        self.voices.append(v)
        self.song._dirty()
        return v

    def pedal(self, mode: str | float = "bar") -> "Section":
        """Sustain pedal, re-applied every bar ("bar"), half bar
        ("half"), or every N beats when given a number."""
        self.pedal_mode = mode
        self.song._dirty()
        return self

    def soft(self, on: bool = True) -> "Section":
        """Una corda: hold the soft pedal (CC67) through the section."""
        self.soft_pedal = on
        self.song._dirty()
        return self

    def swing(self, amount: float = 0.62,
              unit: str = "eighth") -> "Section":
        """Swing this section by its own amount (0.5 is straight), in
        place of the song's: a straight verse into a swung chorus."""
        if unit not in ("eighth", "sixteenth"):
            raise CompositionError('swing: unit is "eighth" or "sixteenth"')
        if not 0 < amount < 1:
            raise CompositionError("swing: amount is between 0 and 1 "
                                   "(0.5 is straight)")
        self.swing_amount, self.swing_unit = amount, unit
        self.song._dirty()
        return self

    def rubato(self, depth: float = 0.05, phrase: int = 2,
               shape: str = "arch") -> "Section":
        """Tempo inflection per phrase: "arch" presses forward through
        the phrase and relaxes its end; "cradle" broadens mid-phrase."""
        if shape not in ("arch", "cradle"):
            raise CompositionError('rubato: shape is "arch" or "cradle"')
        self.rubato_depth = depth
        self.rubato_phrase = phrase
        self.rubato_shape = shape
        self.song._dirty()
        return self

    def time_change(self, bar: int, time: str) -> "Section":
        """Change the meter from `bar` on, bar 1 being the first full
        bar: time_change(5, "3/4"). A voice may write the same change
        inline as M:3/4 at the start of that bar. Bar checks, bar
        numbers, pedaling by the bar, harmony(slots="bar"), and the
        engraving all follow the meters; harmony() sees the changes
        declared before it runs."""
        _meter_beats(time)
        if int(bar) != bar or bar < 1:
            raise CompositionError(
                f"time_change: bar is a bar number from 1 (got {bar!r})")
        self.meters[int(bar)] = time
        self.song._dirty()
        return self

    def _meter_at(self, bar: int) -> tuple[float, str]:
        """(beats per bar, time signature) in force at bar `bar`."""
        time = self.time_sig
        for b in sorted(self.meters):
            if b > bar:
                break
            time = self.meters[b]
        return _meter_beats(time), time

    def _walk(self, start: float, length: float) -> tuple[list, bool]:
        """The full bars from `start` up to `length` beats as (start,
        beats, number, time), and whether the last ends exactly at
        `length`."""
        bars, pos, number = [], start, 1
        while pos < length - 1e-9:
            beats, time = self._meter_at(number)
            bars.append((pos, beats, number, time))
            pos += beats
            number += 1
        return bars, abs(pos - length) < 1e-6

    def _anacrusis_of(self, length: float) -> float:
        """The pickup a passage of `length` beats opens with: the song's
        pickup when the passage is that pickup plus whole bars, else 0."""
        pickup = self.song.pickup
        if not pickup or self._walk(0.0, length)[1]:
            return 0.0
        return pickup if self._walk(pickup, length)[1] else 0.0

    def _anacrusis(self) -> float:
        """Beats of pickup before the section's first downbeat (0.0 when
        it opens on one), judged from the section's length."""
        sec_len = max((v.total_beats() for v in self.voices), default=0.0)
        return self._anacrusis_of(sec_len)

    def bar_grid(self, length: float | None = None) -> list[tuple]:
        """The section's bars as (start beat, beats, bar number, time):
        a pickup as bar 0 when the section opens with one, then the full
        bars in the meters in force."""
        if length is None:
            length = max((v.total_beats() for v in self.voices), default=0.0)
        anac = self._anacrusis_of(length)
        bars = self._walk(anac, length)[0]
        return ([(0.0, anac, 0, self.time_sig)] if anac else []) + bars

    def _bar_index(self, length: float):
        """A function mapping a beat to its bar number (0 for a pickup)."""
        grid = self.bar_grid(length)

        def bar_of(t):
            number = 1
            for start, _beats, n, _time in grid:
                if t < start - 1e-9:
                    break
                number = n
            return number
        return bar_of

    def _bar_position(self, length: float):
        """A function mapping a beat to its fractional bar number, 1.0
        at the first downbeat: bar 3 beat 2 of a 4/4 bar is 3.25. A
        pickup counts back from 1.0, and beats past the end continue in
        the last meter."""
        grid = [g for g in self.bar_grid(length) if g[2] >= 1]
        anac = self._anacrusis_of(length)

        def position(t):
            if not grid:
                return 1.0 + (t - anac) / self.bpb
            if t < grid[0][0]:
                return 1.0 + (t - grid[0][0]) / grid[0][1]
            for start, beats, number, _time in reversed(grid):
                if t >= start - 1e-9:
                    return number + (t - start) / beats
            return 1.0
        return position

    def _bar_beat(self, length: float):
        """The inverse of _bar_position(): a function mapping a
        fractional bar number to its beat in the section."""
        grid = [g for g in self.bar_grid(length) if g[2] >= 1]
        anac = self._anacrusis_of(length)

        def beat(b):
            if not grid:
                return anac + (b - 1.0) * self.bpb
            if b < 1.0:
                return grid[0][0] + (b - 1.0) * grid[0][1]
            for start, beats, number, _time in reversed(grid):
                if b >= number - 1e-9:
                    return start + (b - number) * beats
            return grid[0][0]
        return beat

    def bar_count(self, length: float | None = None) -> float:
        """Bars in the section, a pickup counting as its fraction of the
        first full bar."""
        grid = self.bar_grid(length)
        full = [g for g in grid if g[2] >= 1]
        pickup = grid[0][1] if grid and grid[0][2] == 0 else 0.0
        first = full[0][1] if full else self.bpb
        return len(full) + pickup / first

    def locate(self, t: float) -> str:
        """Render a section-relative beat offset as 'bar B beat N',
        accounting for a pickup and for meter changes."""
        grid = self.bar_grid()
        if not grid:
            return f"bar 1 beat {t + 1:g}"
        start, _beats, number, _time = grid[0]
        for g in grid:
            if t < g[0] - 1e-9:
                break
            start, _beats, number, _time = g
        if number == 0:
            return f"pickup beat {t + 1:g}"
        return f"bar {number} beat {round(t - start, 6) + 1:g}"

    def variant(self, name: str, vel_scale: float = 1.0) -> "Section":
        """Return a copy of this section with velocities scaled. The copy
        keeps the key, time signature, pedal, soft pedal, and rubato, and
        each voice keeps its channel, program, drum and onset modes, and
        notation state, so bars() may continue it."""
        clone = self.song.section(name, key=self.key, time=self.time_sig)
        clone.bpb = self.bpb
        clone.meters = dict(self.meters)
        clone.pedal_mode = self.pedal_mode
        clone.soft_pedal = self.soft_pedal
        clone.rubato_depth = self.rubato_depth
        clone.rubato_phrase = self.rubato_phrase
        clone.rubato_shape = self.rubato_shape
        clone.swing_amount = self.swing_amount
        clone.swing_unit = self.swing_unit

        def scaled(vel):
            return max(15, min(127, int(vel * vel_scale)))
        for v in self.voices:
            nv = Voice(f"{name}.{v.name.split('.', 1)[1]}", self.song,
                       key=v.key, program=v.program, channel=v.channel,
                       bpb=v.bpb, absolute=v.absolute, drums=v.drums)
            nv.section = clone
            nv._oct, nv._dur, nv._started = v._oct, v._dur, v._started
            nv._bars_done, nv._pickup_first = v._bars_done, v._pickup_first
            nv.barlines = list(v.barlines)
            nv._vel = scaled(v._vel)
            if v._cresc_from is not None:
                nv._cresc_from = (v._cresc_from[0], scaled(v._cresc_from[1]))
            nv.pedal_marks = list(v.pedal_marks)
            nv.dyn_marks = dict(v.dyn_marks)
            nv.hairpins = dict(v.hairpins)
            for n in v.notes:
                nv.notes.append(Note(list(n.pitches), n.beats, scaled(n.vel),
                                     n.gate, n.tie, n.grace, n.roll, n.trill,
                                     n.hold, n.marks,
                                     list(n.spell) if n.spell else None,
                                     n.tup,
                                     [scaled(x) for x in n.vels]
                                     if n.vels else None))
            clone.voices.append(nv)
        self.song._dirty()
        return clone

    def _reconcile_pickup(self) -> None:
        """harmony() opens an empty voice with the song's pickup rest when
        it cannot yet know how the section begins; when the voices
        written by hand turn out to open on a downbeat, that rest
        yields, so the order the voices are written in does not matter."""
        if not self.song.pickup:
            return
        auto = [v for v in self.voices
                if v.notes and v.notes[0].marks == "pickup"]
        hand = [v for v in self.voices if v.notes and v not in auto]
        if auto and hand and not any(v._anacrusis() for v in hand):
            for v in auto:
                v.notes.pop(0)
            self.song._dirty()

    def length_beats(self) -> float:
        self._reconcile_pickup()
        for v in self.voices:
            if v._cresc_from is not None:
                raise CompositionError(
                    f"voice '{v.name}': 'cresc'/'dim' never reaches a "
                    f"dynamic mark — follow it with one of !pp..!ff")
            v._check_ties()
            pending = False
            prev = None
            for n in v.notes:
                if n.grace:
                    pending = True
                    continue
                if pending:
                    struck = bool(n.pitches)
                    if (struck and prev is not None and prev.tie
                            and prev.pitches
                            and set(prev.pitches) == set(n.pitches)):
                        struck = False    # a tie continuation, not a strike
                    if not struck:
                        what = ("a rest" if not n.pitches
                                else "a tied continuation")
                        raise CompositionError(
                            f"voice '{v.name}': a grace note must directly "
                            f"precede a struck note, not {what}")
                    pending = False
                prev = n
            if pending:
                raise CompositionError(
                    f"voice '{v.name}': a grace note at the end of the "
                    f"voice has no note to ornament")
        lens = {v.name: v.total_beats() for v in self.voices}
        vals = set(round(x, 4) for x in lens.values())
        if len(vals) > 1:
            pretty = {k: f"{x / self.bpb:.2f} bars" for k, x in lens.items()}
            raise CompositionError(
                f"section '{self.name}': voices differ in length: {pretty}")
        length = next(iter(vals)) if vals else 0.0
        if self.meters:
            # a barline written before a meter change was declared must
            # still fall where the section's meters put one
            starts = {round(g[0], 4) for g in self.bar_grid(length)}
            starts.add(round(length, 4))
            for v in self.voices:
                for pos in v.barlines:
                    if round(pos, 4) not in starts:
                        raise CompositionError(
                            f"voice '{v.name}': a barline at beat {pos:g} "
                            f"falls inside a bar of the section's meters "
                            f"{self.meters} — rewrite the bars around the "
                            f"meter change")
        return length


def _grid(total: int, anac: int, step: int) -> list[int]:
    """Section-relative ticks where a periodic change falls: the start,
    then every `step` ticks from the first downbeat, `anac` ticks in."""
    marks = [0] if anac else []
    pos = anac
    while pos < total:
        marks.append(pos)
        pos += step
    return marks


# Chord templates for analysis, simplest first so a tie keeps the plainer
# reading; intervals are pitch classes above the root.
_ANALYSIS = [("", (0, 4, 7)), ("m", (0, 3, 7)), ("dim", (0, 3, 6)),
             ("aug", (0, 4, 8)), ("sus4", (0, 5, 7)), ("sus2", (0, 2, 7)),
             ("7", (0, 4, 7, 10)), ("maj7", (0, 4, 7, 11)),
             ("m7", (0, 3, 7, 10)), ("m7b5", (0, 3, 6, 10)),
             ("dim7", (0, 3, 6, 9)), ("mmaj7", (0, 3, 7, 11)),
             ("6", (0, 4, 7, 9)), ("m6", (0, 3, 7, 9)),
             ("7sus4", (0, 5, 7, 10)), ("9", (0, 2, 4, 7, 10)),
             ("m9", (0, 2, 3, 7, 10)), ("maj9", (0, 2, 4, 7, 11)),
             ("7b9", (0, 1, 4, 7, 10))]
_PC_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_PC_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def _name_chord(weight: list, bass: int | None, flat: bool) -> str:
    """Name the chord best matching a 12-bin pitch-class weighting (beats
    sounded), with `bass` the lowest pitch sounding: the template that
    covers the most sound, penalized for sound it leaves out and for
    tones it asks for that are absent, favoring a root in the bass. A
    bass other than the root is written as a slash."""
    names = _PC_FLAT if flat else _PC_SHARP
    total = sum(weight)
    present = [pc for pc in range(12) if weight[pc] > 1e-9]
    if not present:
        return "N.C."
    if len(present) == 1:
        return names[present[0]]
    unit = total / len(present)
    best = None
    for root in range(12):
        for rank, (qual, ivs) in enumerate(_ANALYSIS):
            tones = {(root + i) % 12 for i in ivs}
            cover = sum(weight[pc] for pc in tones)
            missing = sum(1 for pc in tones if weight[pc] <= 1e-9)
            score = (cover - (total - cover) - 0.6 * unit * missing
                     - 0.01 * unit * rank)
            if bass is not None and bass % 12 == root:
                score += 0.3 * unit
            if best is None or score > best[0] + 1e-9:
                best = (score, root, qual)
    _score, root, qual = best
    name = names[root] + qual
    if bass is not None and bass % 12 != root:
        name += "/" + names[bass % 12]
    return name


_RUB = {1: "minor second", 11: "major seventh", 13: "minor ninth"}


def _merge_spans(spans) -> list:
    """Sorted (start, end) spans with overlapping ones merged."""
    merged = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _settle(strikes) -> set:
    """Make every key's notes well formed on its channel, in place. A
    note sounds at least _MIN_TICKS; it is released no later than the
    next strike of the same key, as a piano damps a string struck again
    (a later note-off would silence the new note); and strikes of one
    key at one tick merge into the louder and longer. Takes (on, off)
    event lists and returns the ids of the events to drop."""
    drop = set()
    keys = {}
    for on, off in strikes:
        off[0] = max(off[0], on[0] + _MIN_TICKS)
        keys.setdefault((on[2], on[3]), []).append((on, off))
    for seq in keys.values():
        seq.sort(key=lambda s: s[0][0])
        held = None
        for on, off in seq:
            if held is not None:
                h_on, h_off = held
                if on[0] == h_on[0]:
                    h_on[4] = max(h_on[4], on[4])
                    h_off[0] = max(h_off[0], off[0])
                    drop.update((id(on), id(off)))
                    continue
                h_off[0] = min(h_off[0], on[0])
            held = (on, off)
    return drop


class Song:
    def __init__(self, tempo: float = 100, time: str = "4/4",
                 key: str = "C", pickup: float = 0.0, humanize: int = 0,
                 swing: float = 0.5, swing_unit: str = "eighth",
                 expressive: bool = True, fermata: float = 1.55,
                 trill_rate: float = 0.125,
                 pitch_range: tuple[int, int] = (PIANO_LO, PIANO_HI),
                 title: str | None = None, composer: str | None = None,
                 dynamics: dict | None = None):
        self.title = title
        self.composer = composer
        # velocity for each dynamic mark; dynamics= retunes some of them
        # to an instrument's touch
        self.levels = dict(DYN)
        for mark, vel in (dynamics or {}).items():
            if mark not in DYN or not 1 <= int(vel) <= 127:
                raise CompositionError(
                    f"dynamics: {mark!r}={vel!r} — marks are "
                    f"{' '.join(DYN)}, velocities 1-127")
            self.levels[mark] = int(vel)
        self.tempo = tempo
        self.beats_per_bar = _meter_beats(time)
        self.time_sig = time
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
        self._rev = 0              # bumped by every mutator; keys the cache
        self._events_cache = {}    # order -> (signature, (events, cursor))

    def _dirty(self) -> None:
        """Invalidate the memoized event stream after a structural change.
        The built-in composition methods call this. Editing or appending
        Note objects by hand is also caught (the render signature reads
        note content), so calling this yourself is optional but harmless."""
        self._rev += 1
        self._events_cache.clear()

    def _render_sig(self):
        """A value signature of everything the render reads: the mutation
        counter plus each Note's content. Comparing it by value means a
        Note edited in place (which does not bump _rev) still invalidates
        the memoized stream, closing the raw-API cache gap."""
        return (self._rev, tuple(
            (tuple(v.pedal_marks), tuple(
                (tuple(n.pitches), n.beats, n.vel, n.gate,
                 n.tie, n.grace, n.roll, n.trill, n.hold,
                 tuple(n.vels) if n.vels else None)
                for n in v.notes))
            for sec in self.sections.values()
            for v in sec.voices))

    def section(self, name: str, key: str | None = None,
                time: str | None = None) -> Section:
        if name in self.sections:
            raise CompositionError(
                f"section '{name}' already exists — pick a new name "
                f"(a variant needs its own name too)")
        s = Section(name, self, key=key, time=time)
        self.sections[name] = s
        self._dirty()
        return s

    def arrange(self, order: str) -> "Song":
        self.order = order.split()
        for name in self.order:
            if name not in self.sections:
                raise CompositionError(f"arrange: unknown section '{name}'")
        self._dirty()
        return self

    def transpose(self, semitones: int) -> "Song":
        """Shift every already-entered note by a number of semitones,
        in place, and relabel the keys, each voice's signature included,
        so later bars() input, trills, and pitch metrics follow the new
        key. Call it after the sections are written. Raises, changing
        nothing, if any note would leave the instrument range."""
        self._dirty()
        for sec in self.sections.values():
            for v in sec.voices:
                for n in v.notes:
                    for p in n.pitches:
                        if not self.pitch_lo <= p + semitones <= self.pitch_hi:
                            raise CompositionError(
                                f"transpose by {semitones}: MIDI {p} would "
                                f"leave the range {self.pitch_lo}-"
                                f"{self.pitch_hi}")
        mag = abs(semitones)
        steps = (_SEMI_STEPS[mag % 12] + 7 * (mag // 12)) * (
            1 if semitones >= 0 else -1)

        def respell(sp, p):
            """A written spelling moved by the interval, or None when the
            new letter would need more than a double accidental."""
            letter, _alter, octv = sp
            idx = octv * 7 + LETTERS.index(letter) + steps
            nl, no = LETTERS[idx % 7], idx // 7
            alter = p - (12 * (no + 1) + STEP[nl])
            return (nl, alter, no) if -2 <= alter <= 2 else None

        for sec in self.sections.values():
            for v in sec.voices:
                for n in v.notes:
                    n.pitches = [p + semitones for p in n.pitches]
                    if n.spell:
                        spell = [respell(sp, p)
                                 for sp, p in zip(n.spell, n.pitches)]
                        n.spell = spell if all(spell) else None
                v.key = _transpose_key(v.key, semitones)
            if sec.key:
                sec.key = _transpose_key(sec.key, semitones)
        self.key = _transpose_key(self.key, semitones)
        return self

    def tempo_change(self, section: str, bar: int, bpm: float) -> None:
        self._tempo_changes[(section, bar)] = bpm
        self._dirty()

    def ritardando(self, section: str, bar_from: int, bar_to: int,
                   bpm_to: float) -> None:
        """Apply a linear tempo ramp across the given bars. A target
        faster than the prevailing tempo produces an accelerando."""
        self._ramps.append((section, bar_from, bar_to, bpm_to))
        self._dirty()

    @classmethod
    def from_midi(cls, path: str, grid: int | None = 12,
                  section: str = "MIDI") -> "Song":
        """Read a Standard MIDI File into a Song, so its harmony,
        counterpoint, dissonance, and motifs can be examined with
        chords(), lint(), rubs(), find(), and report(), and it can be
        transposed, engraved, or rendered again. It becomes one section,
        `section`. Each track's notes (each channel's, when a track holds
        several) become voices, as many as the notes need: notes struck
        together with the same length form a chord, and a note that
        overlaps the one before it goes to another voice. A voice takes
        its track's name, the further voices of a track numbered from 2
        (rh, rh2), and in a single-track file its channel's (ch1). Onsets
        and lengths snap to 1/`grid` of a beat, so 12 keeps sixteenths
        and triplets, and a note shorter than that takes one step;
        grid=None keeps the file's own resolution, every tick. The
        piece ends at its last release or at the end of its tracks,
        whichever is later, filled out to the barline when that is
        within a beat. The first track's name is the title; the first
        tempo, time signature, and key signature set the song's; a later
        change of meter on a barline becomes time_change(), a later tempo
        a tempo_change() at its beat, the sustain pedal notated ped and
        lift marks, and channel 10 a drum voice. The notes enter as raw
        Note objects, each keeping its own velocity, so notation
        validation does not apply and saving the song again gives back
        the file's notes to the grid."""
        mid = mido.MidiFile(path)
        tpb = mid.ticks_per_beat
        grid = grid or tpb

        def cell(tick):
            """A tick as a whole number of grid steps."""
            return round(tick * grid / tpb)

        tempos, meters, keys, title, ends = [], [], [], None, [0]
        groups, programs, names, pedal = {}, {}, {}, {}
        for ti, track in enumerate(mid.tracks):
            tick, on = 0, {}

            def close(ch, note, end):
                s0, v0 = on.pop((ch, note))
                groups.setdefault((ti, ch), []).append((s0, end, note, v0))

            for msg in track:
                tick += msg.time
                if msg.type == "set_tempo":
                    tempos.append((tick, mido.tempo2bpm(msg.tempo)))
                elif msg.type == "time_signature":
                    meters.append((tick, f"{msg.numerator}/{msg.denominator}"))
                elif msg.type == "key_signature":
                    keys.append((tick, msg.key))
                elif msg.type == "track_name" and msg.name.strip():
                    names.setdefault(ti, msg.name.strip())
                    if ti == 0:
                        title = title or msg.name.strip()
                elif msg.type == "program_change":
                    programs.setdefault(msg.channel, msg.program)
                elif msg.type == "control_change" and msg.control == 64:
                    pedal.setdefault((ti, msg.channel), []).append(
                        (tick, msg.value >= 64))
                elif msg.type == "note_on" and msg.velocity:
                    if (msg.channel, msg.note) in on:   # a restrike ends it
                        close(msg.channel, msg.note, tick)
                    on[(msg.channel, msg.note)] = (tick, msg.velocity)
                elif (msg.type in ("note_on", "note_off")
                      and (msg.channel, msg.note) in on):
                    close(msg.channel, msg.note, tick)
            for ch, note in list(on):
                close(ch, note, tick)
            ends.append(tick)

        pcs = dict(_KEY_PC, **{"D#": 3, "A#": 10, "Cb": 11, "Fb": 4,
                               "E#": 5, "B#": 0})

        def known(key):
            minor = key.endswith("m")
            root = key[:-1] if minor else key
            if root not in pcs:
                return "C"
            return (_PC_MINOR if minor else _PC_KEY)[pcs[root]]

        def valid(time):
            try:
                _meter_beats(time)
                return True
            except CompositionError:
                return False

        # Several events at one tick: the last is the one in force.
        meters = sorted((m for m in meters if valid(m[1])),
                        key=lambda m: m[0])
        keys.sort(key=lambda k: k[0])
        tempos.sort(key=lambda t: t[0])
        time0 = next((t for tk, t in reversed(meters) if tk == 0), "4/4")
        key0 = next((k for tk, k in reversed(keys) if tk == keys[0][0]),
                    "C") if keys else "C"
        bpm0 = next((b for tk, b in reversed(tempos) if tk == 0), 120.0)
        song = cls(tempo=round(bpm0, 3), time=time0, key=known(key0),
                   expressive=False, pitch_range=(0, 127), title=title)
        sec = song.section(section)
        bar, start, bpb, now = 1, 0.0, _meter_beats(time0), time0
        for tick, time in meters:
            n = (cell(tick) / grid - start) / bpb
            if (time != now and round(n) >= 1
                    and abs(n - round(n)) < 1e-6):
                bar, start = bar + round(n), cell(tick) / grid
                bpb, now = _meter_beats(time), time
                sec.time_change(bar, time)

        # The piece ends at its last release or its tracks' end, whichever
        # is later; a note shorter than a grid step takes one, inside it.
        last = max([cell(s1) for notes in groups.values()
                    for _s0, s1, _p, _v in notes] + [cell(max(ends))])
        used, reach = set(), {}
        channels = {}
        for ti, ch in groups:
            channels.setdefault(ti, set()).add(ch)
        for (ti, ch), notes in sorted(groups.items()):
            chords = {}       # (onset, span) in grid steps: {pitch: vel}
            for s0, s1, p, v in notes:
                at, stop = cell(s0), cell(s1)
                if stop <= at:
                    at = max(0, min(at, last - 1))
                    stop = at + 1
                struck = chords.setdefault((at, stop - at), {})
                struck[p] = max(struck.get(p, 0), v)
            layers = []                       # [end, events]
            for (at, span), struck in sorted(chords.items()):
                for layer in layers:
                    if layer[0] <= at:
                        break
                else:
                    layer = [0, []]
                    layers.append(layer)
                layer[1].append((at, span, sorted(struck), struck))
                layer[0] = at + span
            if mid.type == 0:                 # one track: name by channel
                base = f"ch{ch + 1}"
            else:
                base = (re.sub(r"[^0-9A-Za-z]+", "_", names.get(ti, ""))
                        .strip("_").lower() or f"t{ti}")
                if len(channels[ti]) > 1:
                    base += f"_ch{ch + 1}"
            for k, (_end, events) in enumerate(layers):
                name = base if k == 0 else f"{base}{k + 1}"
                while name in used:
                    name += "_"
                used.add(name)
                v = (sec.drums(name) if ch == 9 else
                     sec.voice(name, program=programs.get(ch, 0), channel=ch))
                t = 0
                for at, span, ps, struck in events:
                    if at > t:
                        v.notes.append(Note([], (at - t) / grid, 0))
                    vels = [struck[p] for p in ps]
                    v.notes.append(Note(ps, span / grid, max(vels), gate=1.0,
                                        vels=vels if len(set(vels)) > 1
                                        else None))
                    t = at + span
                reach[v.name] = t
                if k == 0:
                    down = False
                    for tick, press in pedal.get((ti, ch), []):
                        if press or down:
                            v.pedal_marks.append((cell(tick) / grid,
                                                  "ped" if press else "lift"))
                        down = press
        # The last bar is filled out when its barline is within a beat.
        end = max([last] + list(reach.values())) / grid
        bars = sec._walk(0.0, end)[0]
        barline = bars[-1][0] + bars[-1][1] if bars else end
        if barline - end <= 1 + 1e-9:
            end = barline
        for v in sec.voices:
            gap = end - reach[v.name] / grid
            if gap > 1e-9:
                v.notes.append(Note([], gap, 0))
        position = sec._bar_position(end)
        for tick, bpm in tempos:
            if tick > 0:
                song.tempo_change(section, position(cell(tick) / grid),
                                  round(bpm, 3))
        return song

    # ── rendering ────────────────────────────────────────
    def _swing_shift(self, tick: int, sec: "Section | None" = None) -> int:
        """Ticks to delay a note at `tick` (from the first downbeat) under
        the section's swing, or the song's where the section sets none."""
        amount, unit = self.swing, self.swing_unit
        if sec is not None and sec.swing_amount is not None:
            amount, unit = sec.swing_amount, sec.swing_unit
        if abs(amount - 0.5) < 1e-6:
            return 0
        period = TPB if unit == "eighth" else TPB // 2
        if tick % period == period // 2:
            return int((amount - 0.5) * period)
        return 0

    def _base_bpm_fn(self, sec_name: str, barpos):
        # Steps and ramps apply in bar order, so a later instruction
        # overrides an earlier one: (start, kind, end, bpm), a step being
        # a ramp that ends where it starts; a step sorts first at a bar.
        # `barpos` maps a beat to its fractional bar number.
        plan = sorted(
            [(bar, 0, bar, bpm) for (sn, bar), bpm
             in self._tempo_changes.items() if sn == sec_name]
            + [(f, 1, t, bpm) for (sn, f, t, bpm) in self._ramps
               if sn == sec_name])

        def at(pos_ticks):
            # Bar 1 begins at the first downbeat; a pickup before it
            # plays at bar 1's tempo. The comparisons allow for float
            # error, so a change at a fractional bar starts at its tick.
            bar = max(1.0, barpos(pos_ticks / TPB))
            bpm = self.tempo
            for start, _kind, end, target in plan:
                if bar < start - 1e-9:
                    break
                if bar >= end - 1e-9:
                    bpm = target
                else:
                    frac = (bar - start) / max(1e-9, end - start)
                    bpm = bpm + (target - bpm) * frac
            return bpm
        return at, bool(plan)

    def _events(self, order=None):
        """Return (events, cursor), memoized on a content signature so
        repeated report()/events()/save() calls on an unchanged song do
        not re-render. A built-in mutator bumps the counter; a hand-built
        or hand-edited Note is caught by the fingerprint (see _render_sig)."""
        return self._render(order)[1]

    def _events_full(self, order=None):
        """(events, cursor, roles): the memoized render, with the voice
        role of each note event (None for pedal and tempo events), which
        the multi-track MIDI file uses."""
        return self._render(order)[0]

    def _render(self, order):
        key = tuple(order) if order is not None else None
        sig = self._render_sig()
        hit = self._events_cache.get(key)
        if hit is not None and hit[0] == sig:
            return hit[1], hit[2]
        full = self._compute_events(order)
        pair = full[:2]
        self._events_cache[key] = (sig, full, pair)
        return full, pair

    def _compute_events(self, order=None):
        import math
        import random
        rng = random.Random(20)
        events = []
        strikes = []               # (on, off) event pairs, settled at the end
        bpm_now = self.tempo       # the tempo the stream has reached
        cursor = 0

        def strike(on_t, off_t, ch, p, vel, role):
            on = [on_t, "on", ch, p, vel, role]
            off = [off_t, "off", ch, p, 0, role]
            events.extend((on, off))
            strikes.append((on, off))

        order = order or self.order or list(self.sections)
        for sec_name in order:
            if sec_name not in self.sections:
                raise CompositionError(
                    f"unknown section '{sec_name}' — sections are "
                    f"{list(self.sections)}")
            sec = self.sections[sec_name]
            sec_len = sec.length_beats()
            end = round(sec_len * TPB)
            # Bar-relative effects (downbeat lean, swing, pedal changes,
            # tempo plans, rubato phrases) count from the first downbeat,
            # which follows the pickup when the section opens with one,
            # and follow the section's meters.
            grid = sec.bar_grid(sec_len)
            anac = int(round(sec._anacrusis_of(sec_len) * TPB))
            downbeats = {round(g[0] * TPB) for g in grid if g[2] >= 1}
            barpos = sec._bar_position(sec_len)
            holds = []                 # section-relative spans under fermatas
            for v in sec.voices:
                ch = v.channel
                role = v.name.split(".", 1)[1]
                sounding = [n for n in v.notes if n.pitches and not n.grace]
                avg = (sum(p for n in sounding for p in n.pitches)
                       / max(1, sum(len(n.pitches) for n in sounding)))
                tb = 0.0                   # beats into the section
                carried = None
                pending_grace = []
                for i, n in enumerate(v.notes):
                    if n.grace:
                        pending_grace.append(n)
                        continue
                    # ticks from the running beat count, so tuplets whose
                    # members are not whole ticks never drift
                    t = cursor + round(tb * TPB)
                    ticks = cursor + round((tb + n.beats) * TPB) - t
                    tb += n.beats
                    if n.hold:
                        holds.append((t - cursor, t - cursor + ticks))
                    if n.pitches:
                        nxt = next((m for m in v.notes[i + 1:]
                                    if not m.grace), None)
                        if (n.tie and nxt
                                and set(nxt.pitches) == set(n.pitches)):
                            carried = carried if carried is not None else t
                        else:
                            start = carried if carried is not None else t
                            carried = None
                            length = t + ticks - start
                            start += self._swing_shift(start - cursor - anac,
                                                       sec)
                            for gi, g in enumerate(reversed(pending_grace)):
                                gt = max(cursor, start - 60 * (gi + 1))
                                for p in g.pitches:
                                    strike(gt, gt + 55, ch, p, g.vel, role)
                            pending_grace = []
                            vel = n.vel
                            if self.expressive:
                                if start - cursor in downbeats:
                                    vel += 3
                                if not v.drums:
                                    top = max(n.pitches)
                                    vel += max(-6, min(6,
                                                       int((top - avg) / 4)))
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
                            # A roll spreads its strikes over no more than
                            # the chord sounds, so the top note is struck
                            # before the chord is released.
                            spread = 0
                            if n.roll and len(n.pitches) > 1:
                                spread = min(28, max(0, off_t - on_t
                                                     - _MIN_TICKS)
                                             // (len(n.pitches) - 1))
                            for pi, p in enumerate(sorted(n.pitches)):
                                pv = vel
                                if n.vels:          # its own, shaded alike
                                    pv += (n.vels[n.pitches.index(p)]
                                           - n.vel)
                                if (self.expressive and not v.drums
                                        and len(n.pitches) > 1
                                        and p == max(n.pitches)):
                                    pv += 5
                                strike(on_t + pi * spread, off_t, ch, p,
                                       max(1, min(127, pv)), role)
            chans = sorted({v.channel for v in sec.voices})
            if sec.pedal_mode:
                if isinstance(sec.pedal_mode, (int, float)):
                    marks = _grid(end, anac,
                                  max(1, int(sec.pedal_mode * TPB)))
                else:
                    marks = {0} if anac else set()
                    for start, beats, number, _time in grid:
                        if number >= 1:
                            marks.add(round(start * TPB))
                            if sec.pedal_mode == "half":
                                marks.add(round((start + beats / 2) * TPB))
                    marks = sorted(m for m in marks if m < end)
                # re-pedal just after each change and lift just before the
                # next; the last lift falls inside the section
                for a, b in zip(marks, marks[1:] + [end]):
                    for ch in chans:
                        events.append((cursor + a + 10, "cc64", ch, 127, 0,
                                       None))
                        events.append((cursor + max(a + 10, b - 20),
                                       "cc64", ch, 0, 0, None))
            # notated pedaling: 'ped' changes (lift just before the note,
            # press just after), 'lift' releases; the section ends lifted
            down = False
            for pos, kind in sorted({(round(b * TPB), kind)
                                     for v in sec.voices
                                     for b, kind in v.pedal_marks}):
                for ch in chans:
                    if down:
                        events.append((cursor + max(0, pos - 20), "cc64",
                                       ch, 0, 0, None))
                    if kind == "ped":
                        events.append((cursor + pos + 10, "cc64", ch, 127, 0,
                                       None))
                down = kind == "ped"
            if down:
                for ch in chans:
                    events.append((cursor + max(0, end - 20), "cc64", ch, 0, 0,
                                   None))
            if sec.soft_pedal:
                for ch in chans:
                    events.append((cursor + 5, "cc67", ch, 127, 0, None))
                    events.append((cursor + end - 10, "cc67", ch, 0, 0, None))
            # Tempo: the section's plan and rubato beat by beat, divided by
            # Song(fermata=) under every fermata; a section with no plan of
            # its own returns to the song tempo.
            bpm_at, has_plan = self._base_bpm_fn(sec_name, barpos)
            spans = _merge_spans(holds)
            points = (set(_grid(end, anac, TPB))
                      if sec.rubato_depth > 0 or has_plan else set())
            if has_plan:               # a change off the beat, on its tick
                beat_of = sec._bar_beat(sec_len)
                bars = [b for (sn, b) in self._tempo_changes
                        if sn == sec_name]
                bars += [b for (sn, f, t, _bpm) in self._ramps
                         if sn == sec_name for b in (f, t)]
                points.update(tk for tk in (round(beat_of(b) * TPB)
                                            for b in bars)
                              if 0 <= tk < end)
            for a, b in spans:
                points.update(p for p in (a, b) if p < end)
            if abs(bpm_now - self.tempo) > 1e-9:
                points.add(0)
            phrase = sec.rubato_phrase
            for pos in sorted(points):
                bpm = bpm_at(pos)
                if sec.rubato_depth > 0:
                    x = (round(barpos(pos / TPB) - 1.0, 9) % phrase) / phrase
                    bend = sec.rubato_depth * math.sin(math.pi * x)
                    mult = (1.0 + bend if sec.rubato_shape == "arch"
                            else 1.0 - bend)
                    if x > 0.85 and sec.rubato_shape == "arch":
                        mult *= 1.0 - sec.rubato_depth * 1.2
                    bpm *= mult
                if any(a <= pos < b for a, b in spans):
                    bpm /= self.fermata
                bpm_now = bpm
                events.append((cursor + pos, "tempo", 0, bpm, 0, None))
            cursor += end
        drop = _settle(strikes)
        kept = [e for e in events if id(e) not in drop]
        kept.sort(key=lambda e: (e[0], e[1] != "off"))
        return [tuple(e[:5]) for e in kept], cursor, [e[5] for e in kept]

    def _midifile(self, order: list[str] | None = None,
                  tracks: bool = True) -> "mido.MidiFile":
        """The song as a Standard MIDI File. With `tracks`, type 1: a
        conductor track (title, composer, tempo map, time and key
        signatures, a marker at each section) and one named track per
        voice role, each holding its notes and its channel's program
        changes, the pedals of a channel riding on the first track that
        plays it; without, type 0, everything in one track."""
        events, total, roles = self._events_full(order)
        seq = order or self.order or list(self.sections)
        role_order = []
        for name in seq:
            for v in self.sections[name].voices:
                role = v.name.split(".", 1)[1]
                if role not in role_order:
                    role_order.append(role)
        home = {}                      # channel -> the role that carries it
        for name in seq:
            for v in self.sections[name].voices:
                home.setdefault(v.channel, v.name.split(".", 1)[1])
        lanes = {None: []}             # role (None: conductor) -> events
        for role in role_order:
            lanes[role] = []
        # (tick, rank, message): metas first at a tick, then programs,
        # then the rendered stream in its own order
        conductor = lanes[None]
        conductor.append((0, 0, mido.MetaMessage(
            "set_tempo", tempo=mido.bpm2tempo(self.tempo))))
        if self.title:
            conductor.append((0, 0, mido.MetaMessage("track_name",
                                                     name=self.title)))
        if self.composer:
            conductor.append((0, 0, mido.MetaMessage(
                "text", text=f"composer: {self.composer}")))
        current, cursor = {}, 0
        for name in seq:
            sec = self.sections[name]
            ln = sec.length_beats()
            conductor.append((cursor, 0, mido.MetaMessage("marker",
                                                          text=name)))
            conductor.append((cursor, 0, mido.MetaMessage(
                "key_signature", key=sec.key or self.key)))
            prev = None
            for start, _beats, _number, sig in sec.bar_grid(ln):
                if sig != prev:
                    num, den = sig.split("/")
                    conductor.append((cursor + round(start * TPB), 0,
                                      mido.MetaMessage(
                                          "time_signature",
                                          numerator=int(num),
                                          denominator=int(den))))
                    prev = sig
            # each channel's program where a section starts using it or
            # changes it, so a channel can change instrument by section
            for v in sec.voices:
                if current.get(v.channel) != v.program:
                    current[v.channel] = v.program
                    lanes[v.name.split(".", 1)[1]].append(
                        (cursor, 1, mido.Message("program_change",
                                                 channel=v.channel,
                                                 program=v.program)))
            cursor += round(ln * TPB)
        for rank, ((tick, kind, ch, a, b), role) in enumerate(
                zip(events, roles), start=2):
            if kind == "on":
                msg = mido.Message("note_on", channel=ch, note=a, velocity=b)
            elif kind == "off":
                msg = mido.Message("note_off", channel=ch, note=a, velocity=0)
            elif kind in ("cc64", "cc67"):
                msg = mido.Message("control_change", channel=ch,
                                   control=int(kind[2:]), value=a)
                role = home.get(ch)
            else:
                msg = mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(a))
                role = None
            lanes[role].append((tick, rank, msg))
        mid = mido.MidiFile(type=1 if tracks else 0, ticks_per_beat=TPB)
        groups = ([lanes[None]] + [lanes[r] for r in role_order] if tracks
                  else [[e for lane in lanes.values() for e in lane]])
        for index, lane in enumerate(groups):
            tr = mido.MidiTrack()
            if tracks and index:
                tr.append(mido.MetaMessage("track_name",
                                           name=role_order[index - 1]))
            last = 0
            for tick, _rank, msg in sorted(lane, key=lambda e: e[:2]):
                tr.append(msg.copy(time=tick - last))
                last = tick
            tr.append(mido.MetaMessage("end_of_track",
                                       time=max(0, total - last)))
            mid.tracks.append(tr)
        return mid

    def events(self, order: list[str] | None = None) -> list:
        """Return the fully expressive event stream: sorted
        (tick, kind, channel, a, b) tuples at TPB (480) ticks per
        beat, kind in {"on", "off", "cc64", "cc67", "tempo"} with bpm
        in `a` for tempo events. Each key is well formed on its
        channel: its note-ons and note-offs alternate, a note is
        released no later than the next strike of the same pitch, and
        strikes of one key at one tick merge. This is exactly what
        save() and play() render; use it to work below the notation.
        The list is a fresh snapshot; the underlying render is cached
        until the song changes."""
        return list(self._events(order)[0])

    def _count_in_taps(self, count_in: int, pitch: int = 84, vel: int = 26):
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

    def save(self, path: str, only: str | None = None,
             tracks: bool = True) -> str:
        """Write the song to a Standard MIDI File and return the path: a
        type 1 file with a conductor track and a track per voice role,
        which a DAW opens as separate parts, or with tracks=False a
        single-track type 0 file."""
        self._midifile([only] if only else None, tracks).save(path)
        return path

    def play(self, port: str | None = None, only: str | None = None,
             count_in: int = 0, progress=None) -> str:
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

    def lint(self, quiet: bool = False, mode: str = "full",
             only: str | list[str] | None = None) -> list[str]:
        """Check counterpoint across each section's voices, locating
        each finding by bar and beat. Collisions catch two voices
        sounding the same pitch at once, whether struck together or
        struck against a held note. Parallel fifths and octaves are
        checked on both the top and the bottom line of each voice pair,
        sampling the sounding pitch at every onset so a parallel taken
        against a held note is caught, not only note-aligned ones.
        mode="homophonic" reports only collisions, for textures that
        deliberately double melody and accompaniment. mode="strict" adds
        five advisory checks on top of the full set: voice crossings,
        unresolved leading tones, unprepared dissonances struck on a
        beat, extreme or very wide tessitura, and unrolled chords wider
        than a tenth (beyond one hand). These fire on free counterpoint
        by design, so read them, do not fear them. `only` names a
        section, or a list of them, to check alone: a fugato held to
        strict counterpoint inside a homophonic piece. Returns a list of
        finding strings; prints them unless quiet=True."""
        if mode not in ("full", "homophonic", "strict"):
            raise CompositionError(
                'lint: mode is "full", "homophonic", or "strict"')
        all_issues = []
        order = self.order or list(self.sections)
        if only is not None:
            names = [only] if isinstance(only, str) else list(only)
            for name in names:
                if name not in self.sections:
                    raise CompositionError(
                        f"lint: unknown section '{name}' — sections are "
                        f"{list(self.sections)}")
            order = [n for n in order if n in names] or names
        seen = set()
        for sec_name in order:
            if sec_name in seen:
                continue
            seen.add(sec_name)
            sec = self.sections[sec_name]
            anac = sec._anacrusis()   # beats count from the first downbeat
            issues = []
            spans = []
            for v in sec.voices:
                if v.drums:
                    continue          # percussion has no counterpoint
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
                    # Sample each voice's sounding sonority at the union of
                    # onsets and flag consecutive events whose outer lines
                    # move together into the same perfect interval. Reading
                    # the sounding pitch, not only shared onsets, catches a
                    # parallel taken against a note held in the other voice.
                    def sounding(iv, t):
                        for (s, e, p) in iv:
                            if s <= t < e - 1e-9:
                                return p
                        return None
                    times = sorted({s for (s, _e, _p) in iv1}
                                   | {s for (s, _e, _p) in iv2})
                    seen_par = set()
                    prev = None
                    for t in times:
                        p1, p2 = sounding(iv1, t), sounding(iv2, t)
                        if p1 is None or p2 is None:
                            prev = None            # a rest breaks the line
                            continue
                        if prev is not None:
                            _, pp1, pp2 = prev
                            for pick in (max, min):
                                x0, y0 = pick(pp1), pick(pp2)
                                x1, y1 = pick(p1), pick(p2)
                                iv0 = abs(x0 - y0) % 12
                                ivn = abs(x1 - y1) % 12
                                if (x0 != x1 and y0 != y1
                                        and iv0 == ivn and iv0 in (0, 7)):
                                    kind = "octaves" if iv0 == 0 else "fifths"
                                    hi, low = max(x1, y1), min(x1, y1)
                                    dkey = (round(t, 6), kind, hi, low)
                                    if dkey in seen_par:
                                        continue
                                    seen_par.add(dkey)
                                    issues.append(
                                        f"parallel {kind} {n1}/{n2} at "
                                        f"{sec.locate(t)} ({hi}/{low})")
                        prev = (t, p1, p2)
                    if mode != "strict":
                        continue
                    # voice crossing: the lower-register voice sounding
                    # above the higher-register one
                    a1 = [pp for (_s, _e, p) in iv1 for pp in p]
                    a2 = [pp for (_s, _e, p) in iv2 for pp in p]
                    if a1 and a2:
                        hi_iv, lo_iv = ((iv1, iv2)
                                        if sum(a1) / len(a1) >= sum(a2) / len(a2)
                                        else (iv2, iv1))
                        seen_x = set()
                        for t in times:
                            ph, pl = sounding(hi_iv, t), sounding(lo_iv, t)
                            if ph and pl and min(pl) > max(ph):
                                k = round(t, 6)
                                if k not in seen_x:
                                    seen_x.add(k)
                                    issues.append(
                                        f"voice crossing {n1}/{n2} at "
                                        f"{sec.locate(t)} "
                                        f"({min(pl)} over {max(ph)})")
                    # unprepared dissonance: a hard dissonance struck in both
                    # voices on a beat, with neither note held to prepare it
                    seen_d = set()
                    for t in times:
                        tb = t - anac
                        if (round(t, 6) not in on1 or round(t, 6) not in on2
                                or abs(tb - round(tb)) > 1e-6):
                            continue
                        p1, p2 = sounding(iv1, t), sounding(iv2, t)
                        if not p1 or not p2:
                            continue
                        d = abs(max(p1) - max(p2)) % 12
                        if d in (1, 2, 6, 10, 11):
                            k = round(t, 6)
                            if k not in seen_d:
                                seen_d.add(k)
                                issues.append(
                                    f"unprepared dissonance {n1}/{n2} at "
                                    f"{sec.locate(t)} (interval {d})")
            if mode == "strict":
                kn = sec.key or self.key
                root = kn[:-1] if kn.endswith("m") else kn
                tpc = _KEY_PC.get(root)
                ltpc = (tpc - 1) % 12 if tpc is not None else None
                for (name, iv, onsets) in spans:
                    tops = [max(p) for (_s, _e, p) in iv]
                    starts = [s for (s, _e, _p) in iv]
                    for k, tp in enumerate(tops):
                        if ltpc is None or tp % 12 != ltpc:
                            continue
                        nxt = tops[k + 1] if k + 1 < len(tops) else None
                        if nxt is not None and nxt % 12 == tpc:
                            continue                 # resolved up to the tonic
                        if nxt is None or abs(nxt - tp) > 2:   # exposed, not step
                            issues.append(
                                f"unresolved leading tone {name} at "
                                f"{sec.locate(starts[k])} (MIDI {tp})")
                    allp = sorted(pp for (_s, _e, p) in iv for pp in p)
                    if allp:
                        med, span = allp[len(allp) // 2], allp[-1] - allp[0]
                        if med >= 82:
                            issues.append(f"tessitura {name}: median MIDI "
                                          f"{med} sits high")
                        elif med <= 45:
                            issues.append(f"tessitura {name}: median MIDI "
                                          f"{med} sits low")
                        if span > 33:
                            issues.append(f"tessitura {name}: span {span} "
                                          f"semitones is very wide")
                # a chord one hand cannot reach unless it is rolled
                for v in sec.voices:
                    if v.drums:
                        continue
                    t = 0.0
                    for n in v.notes:
                        if n.grace:
                            continue
                        reach = (max(n.pitches) - min(n.pitches)
                                 if len(n.pitches) > 1 else 0)
                        if reach > 16 and not n.roll:
                            issues.append(
                                f"wide chord {v.name} at {sec.locate(t)}: "
                                f"spans {reach} semitones — roll it (&) or "
                                f"split it between the hands")
                        t += n.beats
            if issues and not quiet:
                print(f"[lint] section {sec_name}:")
                for line in issues:
                    print("  " + line)
            all_issues.extend(f"[{sec_name}] {i}" for i in issues)
        if not quiet:
            print(f"[lint] {len(all_issues)} finding(s)")
        return all_issues

    def report(self) -> dict:
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
                    **v.pitch_metrics(),
                })
            out["sections"].append({
                "name": name, "bars": sec.bar_count(ln), "key": sec.key,
                "pedal": sec.pedal_mode, "soft": sec.soft_pedal,
                "rubato": sec.rubato_depth, "voices": voices,
            })
        out["duration_s"] = self._duration_s()
        out["lint"] = self.lint(quiet=True)
        out["rubs"] = self.rubs(quiet=True)
        return out

    def _sections(self, what: str, only) -> list[str]:
        """The sections to examine, in arrangement order, each once:
        all of them, or those `only` names."""
        names = [only] if isinstance(only, str) else list(only or [])
        for name in names:
            if name not in self.sections:
                raise CompositionError(
                    f"{what}: unknown section '{name}' — sections are "
                    f"{list(self.sections)}")
        order = self.order or list(self.sections)
        if names:
            order = [n for n in order if n in names] or names
        return list(dict.fromkeys(order))

    def _pedal_plan(self, sec: "Section", length: float) -> list[tuple]:
        """The stretches, as (start, end) beats, in which a section holds
        the sustain pedal down: its pedal() setting, changed at each bar,
        half bar, or step, and its notated ped and lift marks. A section
        ends lifted."""
        downs = []
        mode = sec.pedal_mode
        if mode:
            anac = sec._anacrusis_of(length)
            if isinstance(mode, (int, float)) and not isinstance(mode, bool):
                marks = [0.0] if anac else []
                pos = anac
                while pos < length - 1e-9:
                    marks.append(pos)
                    pos += float(mode)
            else:
                marks = {0.0} if anac else set()
                for start, beats, number, _t in sec.bar_grid(length):
                    if number >= 1:
                        marks.add(start)
                        if mode == "half":
                            marks.add(start + beats / 2)
                marks = sorted(m for m in marks if m < length - 1e-9)
            downs += list(zip(marks, marks[1:] + [length]))
        down_at = None
        for b, kind in sorted({(b, k) for v in sec.voices
                               for b, k in v.pedal_marks}):
            if down_at is not None and b > down_at + 1e-9:
                downs.append((down_at, b))
            down_at = b if kind == "ped" else None
        if down_at is not None:
            downs.append((down_at, length))
        return sorted(downs)

    def rubs(self, quiet: bool = False,
             only: str | list[str] | None = None,
             min_beats: float = 0.5) -> list[str]:
        """Notes of different voices a minor second, a major seventh, or a
        minor ninth apart that ring together for at least `min_beats`: the
        dissonance a listener hears, which the counterpoint checks in
        lint() do not look for. A note rings until its release, or, when
        the sustain pedal is down then, until the pedal next changes,
        following the section's pedal() setting and its notated ped and
        lift marks; a grace note counts, since under the pedal it rings
        on. Each finding names the two voices, the notes, the interval,
        and how long they sound together, located where the later note
        is struck. `only` names a section, or a list of them. Returns the
        finding strings and prints them unless quiet=True."""
        found = []
        for name in self._sections("rubs", only):
            sec = self.sections[name]
            length = sec.length_beats()
            downs = self._pedal_plan(sec, length)

            def rings_to(end):
                for a, b in downs:
                    if a - 1e-9 <= end < b - 1e-9:
                        return b
                return end

            key = sec.key or self.key

            def label(p, n):
                """The pitch as written, when the note kept its spelling."""
                if n.spell and len(n.spell) == len(n.pitches):
                    letter, alter, octv = n.spell[n.pitches.index(p)]
                    return f"{letter}{_ALTER.get(alter, '')}{octv}"
                return note_name(p, key)

            spans = []
            for v in sec.voices:
                if v.drums:
                    continue
                events, t, graces = [], 0.0, []
                for n in v.notes:
                    if n.grace:
                        graces.append(n)
                        continue
                    if n.pitches:
                        for gi, g in enumerate(reversed(graces)):
                            events.append([max(0.0, t - 0.125 * (gi + 1)),
                                           0.115, g, 1.0, False])
                        last = events[-1] if events else None
                        if (last and last[4]
                                and set(last[2].pitches) == set(n.pitches)
                                and abs(last[0] + last[1] - t) < 1e-6):
                            last[1] += n.beats
                            last[3], last[4] = n.gate, n.tie
                        else:
                            events.append([t, n.beats, n, n.gate, n.tie])
                    graces = []
                    t += n.beats
                role = v.name.split(".", 1)[1]
                for i, (s0, beats, n, gate, tie) in enumerate(events):
                    end = (length if tie and i == len(events) - 1
                           else s0 + beats * gate)
                    end = rings_to(end)
                    spans += [(s0, end, p, role, label(p, n))
                              for p in n.pitches]
            spans.sort(key=lambda x: x[:4])
            active, seen = [], set()
            for s0, e0, p, role, name0 in spans:
                active = [a for a in active if a[1] > s0 + 1e-9]
                for _s1, e1, q, other, name1 in active:
                    d = abs(p - q)
                    overlap = min(e0, e1) - s0
                    if (other == role or d not in _RUB
                            or overlap < min_beats - 1e-9):
                        continue
                    lo, hi = sorted(((q, other, name1), (p, role, name0)))
                    k = (round(s0, 4), lo[:2], hi[:2])
                    if k in seen:
                        continue
                    seen.add(k)
                    both = round(overlap, 3)
                    found.append(
                        f"[{name}] rub {lo[1]}/{hi[1]} at {sec.locate(s0)}: "
                        f"{lo[2]} against {hi[2]} ({_RUB[d]}), ringing "
                        f"together {both:g} beat{'' if both == 1 else 's'}")
                active.append((s0, e0, p, role, name0))
        if not quiet:
            for line in found:
                print("[rubs] " + line)
            print(f"[rubs] {len(found)} finding(s)")
        return found

    def find(self, frag: str, key: str | None = None,
             only: str | list[str] | None = None) -> list[dict]:
        """Every place a motif sounds: the same rhythm and the same
        intervals as `frag`, at any exact transposition, compared on each
        voice's top notes with tied notes joined. Rhythm is where the
        notes are struck, so a staccato statement, or one read from a
        performance by from_midi(), matches the motif as written. `key`
        reads the fragment, the song's key by default. Returns dicts of
        section, voice, at ('bar 3 beat 1'), and semitones, the
        transposition from `frag` as written. A statement altered in any
        interval or onset does not match, so this checks that a motif
        survived a variation intact."""
        motif = _line(frag, key or self.key)
        if not motif:
            raise CompositionError("find: the fragment has no notes")
        out = []
        for name in self._sections("find", only):
            sec = self.sections[name]
            for v in sec.voices:
                if v.drums:
                    continue
                line = v._line()
                for i in range(len(line) - len(motif) + 1):
                    shift = _shape_match(line[i:i + len(motif)], motif)
                    if shift is not None:
                        out.append({"section": name,
                                    "voice": v.name.split(".", 1)[1],
                                    "at": sec.locate(line[i][0]),
                                    "semitones": shift})
        return out

    def chords(self, per: str = "beat") -> list[dict]:
        """Name the harmony that sounds, so an agent can check what it
        wrote against what it meant without listening. Each section in
        arrangement order (a repeat once) is cut into windows of a beat,
        half a bar, or a bar (`per`), counted from the first downbeat so a
        pickup is its own window; every pitched voice's sounding pitch
        classes are weighed by how long they sound in the window, and the
        closest chord template is named, with a slash bass when the lowest
        note is not the root. Runs of one chord merge. Returns dicts of
        section, location ('bar 3 beat 1'), beats, and chord."""
        if per not in ("beat", "half", "bar"):
            raise CompositionError('chords: per is "beat", "half", or "bar"')
        out = []
        seen = set()
        for name in self.order or list(self.sections):
            if name in seen:
                continue
            seen.add(name)
            sec = self.sections[name]
            length = sec.length_beats()
            anac = sec._anacrusis()
            sounding = []
            for v in sec.voices:
                if v.drums:
                    continue
                t = 0.0
                for n in v.notes:
                    if n.grace:
                        continue
                    sounding += [(t, t + n.beats, p) for p in n.pitches]
                    t += n.beats
            edges = {0.0, length}
            if per == "beat":
                k = 0
                while anac + k < length - 1e-9:
                    edges.add(round(anac + k, 9))
                    k += 1
            else:
                for start, beats, number, _time in sec.bar_grid(length):
                    edges.add(round(start, 9))
                    if per == "half" and number >= 1:
                        edges.add(round(start + beats / 2, 9))
            edges = sorted(edges)
            flat = KEYS.get(_resolve_key(sec.key or self.key), (0, "#"))[1] == "b"
            for a, b in zip(edges, edges[1:]):
                weight = [0.0] * 12
                bass = None
                for s0, e0, p in sounding:
                    overlap = min(e0, b) - max(s0, a)
                    if overlap > 1e-9:
                        weight[p % 12] += overlap
                        bass = p if bass is None else min(bass, p)
                chord = _name_chord(weight, bass, flat)
                if out and out[-1]["section"] == name and out[-1]["chord"] == chord:
                    out[-1]["beats"] = round(out[-1]["beats"] + b - a, 6)
                    continue
                out.append({"section": name, "at": sec.locate(a),
                            "beats": round(b - a, 6), "chord": chord})
        return out

    def to_lilypond(self, path: str | None = None) -> str:
        """Engrave the song as LilyPond source: a text score that both
        diffs and typesets. One staff per voice role, concatenated in
        arrangement order, carrying key, time and its changes, tempo,
        pickups, notes, chords, rests, ties, dots, tuplets of any size
        and nesting, grace notes, and staccato, fermata, and arpeggio
        marks; a note that crosses a barline is split there and tied,
        and a drum voice engraves on a drum staff. Returns the source
        and writes it to `path` when given; run it through
        `lilypond file.ly` for a PDF. A note whose length has no written
        form, which only the raw Note API can produce, raises."""
        from fractions import Fraction
        order = self.order or list(self.sections)
        plain = {Fraction(4) / 2 ** k for k in range(8)}   # whole .. 128th
        roles, drum_roles = [], set()
        for name in order:
            for v in self.sections[name].voices:
                r = v.name.split(".", 1)[1]
                if r not in roles:
                    roles.append(r)
                if v.drums:
                    drum_roles.add(r)

        def dur_of(b):
            return _LY_DUR.get(round(float(b), 6))

        def length(b):
            """A LilyPond length for b beats: one (dotted) value, else a
            count of the longest plain value that divides it."""
            if dur_of(b):
                return dur_of(b)
            f = Fraction(b).limit_denominator(64)
            unit = Fraction(4)
            while unit >= Fraction(1, 16) and f % unit:
                unit /= 2
            if unit < Fraction(1, 16):
                raise CompositionError(
                    f"to_lilypond: {b:g} beats has no written length")
            return f"{dur_of(unit)}*{f / unit}"

        def pieces(b):
            """Written values summing to b beats, longest first, when b is
            a sum of plain and dotted values (a long chord in an odd meter,
            a rest before an onset anchor); None otherwise."""
            f = Fraction(b).limit_denominator(64)
            out = []
            for val in sorted(_LY_DUR, reverse=True):
                while f >= Fraction(val):
                    out.append(_LY_DUR[val])
                    f -= Fraction(val)
            return out if f == 0 else None

        def tuplet(b):
            """(group size, written value, ratio denominator) for tuplet
            members of b beats: the fewest members whose total is a
            written length, each written as the shortest plain value no
            shorter than b."""
            fb = Fraction(b).limit_denominator(64)
            w = Fraction(4)
            while w / 2 >= fb:
                w /= 2
            for size in range(2, 65):
                den = fb * size / w
                if dur_of(fb * size) and dur_of(w) and den.denominator == 1:
                    return size, dur_of(w), den.numerator
            raise CompositionError(
                f"to_lilypond: a note of {b:g} beats has no written form "
                f"— give raw Note objects lengths the notation can write")

        def head(kn, ts, drums):
            n, d = ts.split("/")
            if drums:
                return f"\\time {n}/{d} "
            minor = kn.endswith("m")
            base = kn[:-1] if minor else kn
            root = base[0].lower() + base[1:].replace("#", "s").replace("b", "f")
            return (f"\\key {root} \\{'minor' if minor else 'major'} "
                    f"\\time {n}/{d} ")

        def pitch_names(n, flat):
            """Each pitch as written when the note kept its spelling,
            else spelled by the key's direction, low to high."""
            if n.spell and len(n.spell) == len(n.pitches):
                return [_ly_spelled(*sp) for _p, sp in
                        sorted(zip(n.pitches, n.spell))]
            return [_ly_pitch(p, flat) for p in sorted(n.pitches)]

        def note_str(n, flat, drums):
            if drums:
                missing = [p for p in n.pitches if p not in _LY_DRUM]
                if missing:
                    raise CompositionError(
                        f"to_lilypond: no drum name for MIDI {missing[0]}")
                names = [_LY_DRUM[p] for p in sorted(n.pitches)]
            else:
                names = pitch_names(n, flat)
            return names[0] if len(names) == 1 else "<" + " ".join(names) + ">"

        def marks(n):
            """(attack, release): accents, tenuto, staccato, and arpeggio
            sit on the first written value of a note, a fermata on its
            last."""
            attack = "".join(a for m, a in ((">", "->"), ("_", "--"))
                             if m in n.marks)
            if n.gate <= 0.5:
                attack += "-."
            if n.roll and len(n.pitches) > 1:
                attack += "\\arpeggio"
            return attack, ("\\fermata" if n.hold else "")

        def bar_start(grid, bar):
            """The beat where bar number `bar` begins, continuing past the
            section's end in its last meter."""
            full = [g for g in grid if g[2] >= 1]
            for start, _beats, number, _time in full:
                if number == bar:
                    return start
            if not full:
                return 0.0
            start, beats, number, _time = full[-1]
            return start + (bar - number) * beats

        def cues(sec_name, sec):
            """Beat -> tempo mark for the section: a step change as a
            metronome mark, a ramp as rit. or accel., both in one mark
            where they start together."""
            length = sec.length_beats()
            grid = sec.bar_grid(length)
            bpm_at, _has_plan = self._base_bpm_fn(
                sec_name, sec._bar_position(length))
            marks_at = {}
            for (sn, bar), bpm in self._tempo_changes.items():
                if sn == sec_name:
                    b = bar_start(grid, bar)
                    marks_at.setdefault(b, ["", ""])[1] = (
                        f"4 = {int(round(bpm))}")
            for sn, f, t, bpm in self._ramps:
                if sn == sec_name:
                    b = bar_start(grid, f)
                    if t <= f:               # a ramp of no length is a step
                        marks_at.setdefault(b, ["", ""])[1] = (
                            f"4 = {int(round(bpm))}")
                        continue
                    # against the tempo in force where the ramp begins
                    was = bpm_at(round(b * TPB))
                    if abs(bpm - was) > 1e-9:
                        word = "rit." if bpm < was else "accel."
                        marks_at.setdefault(b, ["", ""])[0] = f'"{word}"'
            return {b: "\\tempo " + " ".join(x for x in m if x) + " "
                    for b, m in marks_at.items()}

        def meter_marks(sec, grid):
            """Beat -> \\time command where the meter changes inside the
            section (the section's opening meter is in its head)."""
            marks_at, prev = {}, sec.time_sig
            for start, _beats, number, sig in grid:
                if number >= 1 and sig != prev:
                    marks_at[start] = f"\\time {sig} "
                prev = sig if number >= 1 else prev
            return marks_at

        def written(b):
            """Written values for b beats: one value, else a tied sum of
            values, else a counted length."""
            d = dur_of(b)
            if d:
                return [d]
            return pieces(b) or [length(b)]

        def tuplet_ratio(members, span):
            """(normal notes, written value) for a tuplet of `members`
            filling `span` written beats: None when each member is itself
            a written value (a duplet in 6/8 needs no bracket); else the
            plain value the members are written as and how many of it
            fill the span, the count nearest below the members first (3
            in the time of 2, 5 of 4, 7 of 4, 9 of 8)."""
            if dur_of(span / members):
                return None
            for m in (list(range(members - 1, 0, -1))
                      + list(range(members + 1, 4 * members + 1))):
                if span / m in plain:
                    return m, span / m
            for m in range(1, 4 * members + 1):
                if dur_of(span / m):
                    return m, span / m
            raise CompositionError(
                f"to_lilypond: {members} tuplet members in {float(span):g} "
                f"beats have no written form")

        def body(v, flat, tempo_at, meters_at, bars, last_section):
            out, grace, notes, i, pos = [], [], v.notes, 0, 0.0
            pedal = sorted(v.pedal_marks)
            down = False
            tempo_at = dict(tempo_at)
            meters_at = dict(meters_at)

            def before(at):
                """Tempo and meter marks due at beat `at`, emitted ahead of
                a note."""
                s = "".join(meters_at.pop(b) for b in
                            sorted(b for b in meters_at if b <= at + 1e-9))
                due = sorted(b for b in tempo_at if b <= at + 1e-9)
                return s + "".join(tempo_at.pop(b) for b in due)

            def segments(at, beats):
                """[at, at + beats) cut at the barlines inside it, as
                (start, length) pieces."""
                cuts = [b for b in bars if at + 1e-9 < b < at + beats - 1e-9]
                out_, s = [], at
                for c in cuts + [at + beats]:
                    out_.append((s, c - s))
                    s = c
                return out_

            def held(text, at, beats, first, last, tie_out):
                """A sounding note or chord of `beats` beats at `at`,
                split at barlines and tied across them: `first` rides on
                its first written value, `last` on its last."""
                vals = []
                for s, ln in segments(at, beats):
                    for k, x in enumerate(written(ln)):
                        vals.append((before(s) if k == 0 else "", x))
                return " ".join(
                    lead + text + x + (first if k == 0 else "")
                    + (last if k == len(vals) - 1 else "")
                    + ("~" if k < len(vals) - 1 or tie_out else "")
                    for k, (lead, x) in enumerate(vals))

            def silent(at, beats, first):
                """A rest, split at barlines."""
                vals = []
                for s, ln in segments(at, beats):
                    for k, x in enumerate(written(ln)):
                        vals.append((before(s) if k == 0 else "", x))
                return " ".join(lead + "r" + x + (first if k == 0 else "")
                                for k, (lead, x) in enumerate(vals))

            def group(idxs, level, scale):
                """The tuplet at `level` of the notes idxs (consecutive
                members of one group): its members written at the scale
                of the enclosing tuplets, nested groups within."""
                nonlocal pos
                _gid, members, span = notes[idxs[0]].tup[level]
                span_w = Fraction(span).limit_denominator(4096) / scale
                ratio = tuplet_ratio(members, span_w)
                inner = scale if ratio is None else scale * Fraction(
                    ratio[0], members)
                parts, k = [], 0
                while k < len(idxs):
                    j = idxs[k]
                    g = notes[j]
                    if len(g.tup) > level + 1:
                        sub_id = g.tup[level + 1][0]
                        sub = [x for x in idxs[k:] if len(notes[x].tup)
                               > level + 1 and notes[x].tup[level + 1][0]
                               == sub_id]
                        parts.append(group(sub, level + 1, inner))
                        k += len(sub)
                        continue
                    wd = dur_of(Fraction(g.beats).limit_denominator(4096)
                                / inner)
                    if wd is None:
                        raise CompositionError(
                            f"to_lilypond: a tuplet member of {g.beats:g} "
                            f"beats has no written form")
                    lead = before(pos)
                    parts.append(
                        lead + (("r" + wd) if not g.pitches
                                else note_str(g, flat, v.drums) + wd)
                        + after(j, pos) + ("~" if g.tie else ""))
                    pos += g.beats
                    k += 1
                if ratio is None:
                    return " ".join(parts)
                return (f"\\tuplet {members}/{ratio[0]} {{ "
                        + " ".join(parts) + " }")

            def after(j, at):
                """Dynamics, hairpins, and pedal marks for note j at beat
                `at`, written after its duration."""
                nonlocal down
                s = ""
                if j in v.dyn_marks:
                    s += "\\" + v.dyn_marks[j]
                if j in v.hairpins:
                    s += "\\" + v.hairpins[j]
                while pedal and pedal[0][0] <= at + 1e-9:
                    _b, kind = pedal.pop(0)
                    if kind == "ped":
                        s += ("\\sustainOff\\sustainOn" if down
                              else "\\sustainOn")
                    elif down:
                        s += "\\sustainOff"
                    down = kind == "ped"
                return s

            while i < len(notes):
                n = notes[i]
                if n.grace:
                    grace.append(pitch_names(n, flat)[0] + "8")
                    i += 1
                    continue
                if grace:
                    out.append("\\grace { " + " ".join(grace) + " }")
                    grace = []
                if n.trill and n.pitches:           # a trill, written whole
                    j, total = i, 0.0
                    while j < len(notes):
                        total += notes[j].beats
                        if "%" in notes[j].marks:
                            break
                        j += 1
                    last_note = notes[min(j, len(notes) - 1)]
                    out.append(held(pitch_names(n, flat)[0], pos, total,
                                    after(i, pos) + "\\trill", "",
                                    last_note.tie))
                    pos += total
                    i = j + 1
                    continue
                if n.tup:                           # a written tuplet
                    gid = n.tup[0][0]
                    idxs = []
                    while (i < len(notes) and notes[i].tup
                           and notes[i].tup[0][0] == gid):
                        idxs.append(i)
                        i += 1
                    out.append(group(idxs, 0, Fraction(1)))
                    continue
                d = dur_of(n.beats)
                if not d and pieces(n.beats) is None and not any(
                        pos + 1e-9 < b < pos + n.beats - 1e-9 for b in bars):
                    b = n.beats                     # a figure of equal
                    size, wd, den = tuplet(b)       # tuplet-length notes
                    grp = []
                    while (i < len(notes) and not notes[i].grace
                           and not notes[i].tup
                           and abs(notes[i].beats - b) < 1e-9):
                        grp.append((i, notes[i]))
                        i += 1
                    for k in range(0, len(grp), size):
                        inner = []
                        for j, g in grp[k:k + size]:
                            lead = before(pos)
                            inner.append(
                                lead + (("r" + wd) if not g.pitches
                                        else note_str(g, flat, v.drums) + wd)
                                + after(j, pos) + ("~" if g.tie else ""))
                            pos += b
                        out.append(f"\\tuplet {size}/{den} {{ "
                                   + " ".join(inner) + " }")
                    continue
                if not n.pitches:
                    out.append(silent(pos, n.beats, after(i, pos)))
                else:
                    attack, release = ("", "") if v.drums else marks(n)
                    out.append(held(note_str(n, flat, v.drums), pos, n.beats,
                                    attack + after(i, pos), release, n.tie))
                pos += n.beats
                i += 1
            if down and not last_section:   # lift where the section ends; the
                out.append("s1*0\\sustainOff")  # piece's end closes the last
            return " ".join(out)

        staves = []
        for r_index, role in enumerate(roles):
            drums = role in drum_roles
            parts = []
            for index, name in enumerate(order):
                sec = self.sections[name]
                kn = sec.key or self.key
                flat = KEYS.get(_resolve_key(kn), (0, "#"))[1] == "b"
                v = next((x for x in sec.voices
                          if x.name.split(".", 1)[1] == role), None)
                sec_len = sec.length_beats()
                grid = sec.bar_grid(sec_len)
                anac = sec._anacrusis_of(sec_len)
                meters_at = meter_marks(sec, grid)
                seg = head(kn, sec.time_sig, drums)
                if anac:
                    seg += f"\\partial {length(anac)} "
                if v is None:
                    rests = [f"R{length(anac)}"] if anac else []
                    run, count = None, 0
                    for start, beats, number, _time in grid:
                        if number < 1:
                            continue
                        mark = meters_at.get(start, "")
                        if run is not None and (mark or beats != run[1]):
                            rests.append(run[0] + f"R{length(run[1])}"
                                         + (f"*{count}" if count > 1 else ""))
                            run, count = None, 0
                        if run is None:
                            run = (mark, beats)
                        count += 1
                    if run is not None:
                        rests.append(run[0] + f"R{length(run[1])}"
                                     + (f"*{count}" if count > 1 else ""))
                    seg += " ".join(rests)
                else:
                    # tempo marks ride on the first role present here
                    carrier = next(r for r in roles
                                   if any(x.name.split(".", 1)[1] == r
                                          for x in sec.voices))
                    seg += body(v, flat,
                                cues(name, sec) if role == carrier else {},
                                meters_at, [g[0] for g in grid if g[0] > 0],
                                index == len(order) - 1)
                parts.append(seg)
            kind, mode = ("DrumStaff", "\\drummode ") if drums else ("Staff", "")
            # a staff that lives below middle C reads in the bass clef
            sounded = sorted(p for name in order
                             for x in self.sections[name].voices
                             if x.name.split(".", 1)[1] == role
                             for n in x.notes for p in n.pitches)
            clef = ("\\clef bass " if not drums and sounded
                    and sounded[len(sounded) // 2] < 57 else "")
            staves.append(
                f'  \\new {kind} \\with {{ instrumentName = "{role}" }} '
                f'{mode}{{\n'
                f'    {clef}\\tempo 4 = {int(round(self.tempo))} '
                + " ".join(parts) + "\n  }")
        # two pitched staves and nothing else are one piano's two hands
        if len(staves) == 2 and not drum_roles:
            staves = ["  \\new PianoStaff <<\n"
                      + "\n".join("  " + x.replace("\n", "\n  ") for x in staves)
                      + "\n  >>"]

        def quoted(text):
            return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
        header = ""
        if self.title or self.composer:
            header = ("\\header {\n"
                      + (f"  title = {quoted(self.title)}\n" if self.title
                         else "")
                      + (f"  composer = {quoted(self.composer)}\n"
                         if self.composer else "")
                      + "}\n\n")
        src = ('\\version "2.24.0"\n\\language "english"\n\n' + header
               + "\\score {\n  <<\n"
               + "\n".join(staves) + "\n  >>\n  \\layout { }\n}\n")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(src)
        return src

    def describe(self) -> None:
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
            if sec.meters:
                extras.append("meters " + ", ".join(
                    f"{t} at bar {b}" for b, t in sorted(sec.meters.items())))
            if sec.pedal_mode:
                extras.append(f"pedal={sec.pedal_mode}")
            if sec.soft_pedal:
                extras.append("soft")
            if sec.rubato_depth:
                extras.append(f"rubato={sec.rubato_depth}")
            if sec.swing_amount is not None:
                extras.append(f"swing={sec.swing_amount}")
            chans = {v.channel for v in sec.voices}
            if chans != {0}:
                extras.append(f"channels={sorted(chans)}")
            print(f"  [{name}] {sec.bar_count(ln):.1f} bars, "
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
DUR    w h q e s t x [+ . or ..]  sticky;  r = rest (re = eighth rest)
REPEAT c4e*4   (c4e d4e)*3   (c4w |)*8      tokens or groups, barlines allowed
CHORD  [c4 e g]h   TUPLET {c d e}q or {[c4 e4] d4}q   GRACE +d5   TIE c5h~
        tuplets nest: {c4 {d4 e4 f4} g4}q
MARKS  > accent  ' stacc  _ legato  ^ fermata (holds time; rh^ = pause)
        & roll  % trill
PEDAL  ped (press, or change at the next note)   lift (release)
DYN    !ppp !pp !p !mp !mf !f !ff !fff   cresc/dim toward next !dyn
BAR    | must be exactly full (pickup= allows short OR full first bar)
METER  M:3/4 opens a bar: the meter from there on, for the whole section
LV     a tie on a voice's final note lets it ring (laissez vibrer)
ONSET  c5e@3  absolute onset at beat 3 (voice.absolute_onsets() to opt in;
        fills a gap with a rest, errors if earlier material drifted past it)
DRUMS  section.drums(); write names not pitches: bde hh sn hh | [bd hh]q ...
        bd sn hh ho hp lt mt ht cr rd cb rim clap ... (channel 10)
HARMONY voice.harmony("C Am7 F G7", style=block|root|fifth|waltz|
        alberti|arp|broken|stride, voicing=plain|smooth|shell|rootless|drop2,
        slots=bar|half|beats, avoid=<voice>)  qualities incl 9 11 13 7b9 mmaj7
        pattern="0 2 3 4 3 2", unit=1/3   any figure over the chord's ladder
        pattern="0:e. 4:s 2+3:e 2+3:e"   steps with their own lengths
TRANSFORMS shift(frag,n) invert(frag,axis) retro(frag)
        stretch(frag, any factor) rebar(frag, beats_per_bar)
        transpose(frag, semitones, key=)   chromatic, spelled by interval
        double(frag, degrees)   octaves (7, -7) or thirds (-2) added
        harmonize(frag, "Dm A7", key=, voices=3, bass=, slots=)
                chords under a melody, no parallels against the bass
        map_notes(frag, fn, key=)   fn(n) -> pitch | [pitches] | [] | None
HELPERS chord_pitches(sym) scale_pitches(key) note_pitch("c#5", key=)
        note_name(61, key=) transpose_chords("C G7/B", semitones, key=)
        chord_tone_below(pitch, sym, gap=3) same_shape(frag_a, frag_b)
SONG   Song(tempo,time,key,pickup,humanize,swing,swing_unit,
        expressive,fermata,trill_rate,title,composer,dynamics={"p": 45})
       .section(name,key=,time=) .arrange("A A B A") .events()
       .tempo_change(sec,bar,bpm) .ritardando(sec,from,to,bpm)
       .describe() .lint(mode=full|homophonic|strict, only=) .report()
       .chords(per=) .save(path, tracks=)   type 1: a track per voice role
       .to_lilypond() .play(port=,only=,count_in=,progress=)
REPORT per-voice pitch metrics: pitch_classes, out_of_key_rate, intervals,
       self_similarity, grace.  strict lint adds crossings, unresolved
       leading tones, unprepared dissonances, tessitura, wide chords.
CHORDS song.chords(per="beat"|"half"|"bar") names what sounds: check the
       progression you meant against the one you wrote.
RUBS   song.rubs(only=, min_beats=0.5)   notes of two voices a minor 2nd,
       major 7th, or minor 9th apart ringing together, pedal included
FIND   song.find(frag)   each place a motif sounds, at any transposition
MIDI   Song.from_midi(path, grid=12)   a MIDI file as a Song to analyze;
       grid=None keeps every tick
SECTION .voice(name,vel,octave,program,channel,absolute=) .drums(name,vel)
        .pedal("bar"|"half"|N) .soft() .rubato(...) .swing(amount, unit)
        .time_change(bar, "3/4") .variant(name, vel_scale)
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

    # A tie not followed by the same pitch is rejected at parse time.
    dangling = Song().section("D").voice("m")
    try:
        dangling.bars("c4h~ d4h |")
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

    # retro reverses tuplet members, keeps a grace with its note, and
    # writes sticky octaves and durations out explicitly.
    assert retro("{c4 d4 e4}q f4q") == "f4q {e4 d4 c4}q"
    assert retro("+d5 c5q e5q") == "e5q +d5 c5q"
    assert retro("c5q d e") == "e5q d5q c5q"

    # A trill too short to alternate is rejected.
    try:
        Song().section("TR").voice("m").bars("c4s% c4s c4e c4q c4h |")
        raise AssertionError("trill length check did not fire")
    except CompositionError as e:
        assert "trill" in str(e)

    # A chord member must not carry its own duration.
    try:
        Song().section("CM").voice("m").bars("[c4q e4]h [c4 e4]h |")
        raise AssertionError("chord member duration check did not fire")
    except CompositionError as e:
        assert "after the ']'" in str(e)

    # A duplicate section name is rejected rather than replaced.
    dup = Song()
    dup.section("A")
    try:
        dup.section("A")
        raise AssertionError("duplicate section check did not fire")
    except CompositionError as e:
        assert "already exists" in str(e)

    # A harmony figure cannot leave the instrument range silently.
    try:
        Song().section("HR").voice("m").harmony("C", style="stride",
                                                octave=1)
        raise AssertionError("harmony range check did not fire")
    except CompositionError as e:
        assert "range" in str(e)

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
