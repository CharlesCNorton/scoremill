#!/usr/bin/env python3
"""Prelude alla marcia in C minor. In the manner of Rachmaninoff.

A march in dotted rhythms, chords on the strong beats over a leaping
bass; a broad song in E-flat over triplet arpeggios figured by
harmony(pattern=), its second phrase joined by an alto line and rising
to the minor-iv sigh (C to C-flat), its third phrase sung by the cello
register under shimmering arpeggios and held on a fermata; a drumming
dominant pedal back to the march, now fff with notated pedaling on the
climax; and a coda where the march recedes under the soft pedal and a
last arpeggio rises out of it."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, chord_pitches

LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
ACCS = {"": 0, "n": 0, "#": 1, "b": -1, "##": 2, "bb": -2}
FLATS = ["cn", "db", "dn", "eb", "en", "fn", "gb", "gn", "ab", "an", "bb", "bn"]
NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.{0,2})?([~>'_^&]*)$")
KEY_FLATS = {"b": -1, "e": -1, "a": -1}      # C minor / E-flat major


def midi(l, a, o):
    alter = ACCS[a] if a else KEY_FLATS.get(l, 0)
    return 12 * (int(o) + 1) + LETTER[l] + alter


def nm(m):
    return f"{FLATS[m % 12]}{m // 12 - 1}"


def filled(frag, symbol, strong=("q", "q.", "h", "h.", "w")):
    """Put two chord tones of `symbol` under every strong melody note
    (a quarter or longer), leaving the quick notes single."""
    pcs = {p % 12 for p in chord_pitches(symbol)}
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m or (m.group(4) or "") not in strong:
            out.append(tok)
            continue
        top = midi(*m.group(1, 2, 3))
        below = [p for p in range(top - 1, top - 13, -1)
                 if p % 12 in pcs and p % 12 != top % 12][:2]
        chord = sorted(below) + [top]
        out.append("[" + " ".join(map(nm, chord)) + "]"
                   + m.group(4) + (m.group(5) or ""))
    return " ".join(out)


def octaves_up(frag):
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        p = midi(*m.group(1, 2, 3))
        out.append(f"[{nm(p)} {nm(p + 12)}]" + (m.group(4) or "")
                   + (m.group(5) or ""))
    return " ".join(out)


def join(items):
    return " | ".join(items) + " |"


MARCH = [  # (chord, melody in the march rhythm)
    ("Cm", "g5q.> g5e g5e. ab5s g5q"), ("Cm", "c6q.> bb5e ab5e. g5s f5q"),
    ("Fm6", "eb5q.> f5e ab5e. c6s d6q"), ("G7", "bn5q.> g5e f5e. d5s bn4q"),
    ("Cm", "c5q.> c5e eb5e. g5s c6q"), ("Ab", "c6q.> eb6e c6e. ab5s eb5q"),
    ("Dm7b5", "f5q.> ab5e f5e. dn5s ab4q"), ("G7", "bn4q.> dn5e f5e. ab5s g5q"),
    ("Cm", "g5q.> g5e g5e. ab5s g5q"), ("Eb", "bb5q.> g5e eb5e. g5s bb5q"),
    ("Fm", "c6q.> ab5e f5e. ab5s c6q"), ("Bb7", "dn6q.> c6e bb5e. ab5s f5q"),
    ("Eb", "eb6q.> dn6e eb6e. f6s g6q"), ("Ab", "ab6q.> g6e f6e. eb6s c6q"),
    ("D7", "dn6q.> c6e an5e. f#5s dn5q"), ("G", "g5h> [bn4 dn5 g5]h"),
]
BASS = {"Cm": ("c2 c3", "g1 g2"), "Fm6": ("f1 f2", "c2 c3"),
        "G7": ("g1 g2", "dn2 dn3"), "Ab": ("ab1 ab2", "eb2 eb3"),
        "Dm7b5": ("dn2 dn3", "ab1 ab2"), "Eb": ("eb2 eb3", "bb1 bb2"),
        "Fm": ("f1 f2", "c2 c3"), "Bb7": ("bb1 bb2", "f2 f3"),
        "D7": ("dn2 dn3", "an1 an2"), "G": ("g1 g2", "dn2 dn3")}


def march_bass(chord, accent=""):
    root, fifth = BASS[chord]
    return (f"[{root}]q'{accent} [{fifth}]q' [{root}]q'{accent} [{fifth}]q'")


s = Song(tempo=112, time="4/4", key="Cm", humanize=1, expressive=True,
         title="Prelude alla marcia in C minor",
         composer="after Rachmaninoff")

# ── A: the march ──
A = s.section("A")
rh = [filled(m, c) for c, m in MARCH]
rh[15] = "g5h> [bn4 dn5 g5]h"
A.voice("rh").bars(join([
    "!mp " + rh[0], rh[1], "cresc " + rh[2], rh[3], rh[4], rh[5], rh[6],
    "!f " + rh[7], "!mp " + rh[8], rh[9], "cresc " + rh[10], rh[11],
    "!ff " + rh[12], rh[13], "dim " + rh[14], "!mf " + rh[15]]))
lh = [march_bass(c) for c, _m in MARCH]
lh[0] = "!mp " + lh[0]
lh[2] = "cresc " + lh[2]
lh[7] = "!f " + lh[7]
lh[8] = "!mp " + lh[8]
lh[10] = "cresc " + lh[10]
lh[12] = "!ff " + lh[12]
lh[14] = "dim " + lh[14]
lh[15] = "!mf [g1 g2]h> [g1 g2]h"
A.voice("lh").bars(join(lh))

# ── B: the song in E-flat ──
B = s.section("B", key="Eb")
SONG1 = ["bb4h. g4q", "ab4q. c5e eb5q. dn5e", "c5q bb4q bb4q. ab4e", "g4w",
         "g4q. ab4e bb4q c5q", "c5h. cb5q", "bb4q. c5e bb4q ab4q", "g4h. bb4q"]
SONG2 = ["c5h. eb5q", "f5q. eb5e db5q. eb5e", "g5h. f5q",
         "ab5q. g5e f5q. eb5e", "dn5q. eb5e f5q. g5e", "c6h. cb6q",
         "bb5q. c6e bb5q ab5q", "g5w^"]
HARM1 = "Eb Eb/G Ab Fm7 Eb/Bb Bb7 Eb Eb Cm Cm/Bb Fm/Ab Abm6 Eb/Bb Bb7 Eb Eb7"
HARM2 = "Ab Ab/C Db9 Db9 Eb/G Gm7 Fm7 Bb7 Gm7 C7 Fm7 Abm6 Eb/Bb Bb7 Eb Eb"
B.voice("rh").bars(join(
    ["!p " + SONG1[0]] + SONG1[1:5] + ["cresc " + SONG1[5], "!mp " + SONG1[6],
                                        SONG1[7]]
    + ["cresc " + SONG2[0], SONG2[1], "!mf " + SONG2[2], "cresc " + SONG2[3],
       SONG2[4], "!f " + SONG2[5], "dim " + SONG2[6], "!p " + SONG2[7]]))
B.voice("alto").bars(
    "(rw |)*8 !p ab4w | ab4h. cb5q | bb4w | c5h dn5h | bb4h bb4h |"
    " cresc ab4h. ab4q | !mp g4h f4h | eb4w^ |")
arps = B.voice("lh", vel=34)
arps.harmony(HARM1 + " " + HARM2, slots="half", octave=2,
             pattern="0 2 3 4 3 2", unit=1 / 3)
B.pedal("half")
B.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("B", 1, 66)
s.ritardando("B", 15, 17, 52)

# ── B3: the cello sings, arpeggios above ──
B3 = s.section("B3", key="Eb")
tenor = [octaves_up(re.sub(r"(\D)(\d)", lambda m: m.group(1)
                           + str(int(m.group(2)) - 2), t))
         for t in SONG1]
tenor[7] = "[g2 g3]w^"
B3.voice("tenor").bars(join(["!mf " + tenor[0]] + tenor[1:5]
                            + ["cresc " + tenor[5], "!f " + tenor[6],
                               "dim " + tenor[7] + " !mp"]))
hi = B3.voice("hi", vel=30)
hi.harmony("Eb Eb Ab Fm7 Eb Bb7 Eb*2 Cm*2 Fm Abm6 Eb Bb7 Eb*2", slots="half",
           octave=4, pattern="0 1 2 3 2 1", unit=1 / 3)
B3.voice("bass").bars(
    "!p eb2h g1h | ab1h f1h | bb1h bb1h | eb2h eb2h | c2h bb1h |"
    " ab1h ab1h | bb1h bb1h | eb1w^ |")
B3.pedal("half")
B3.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("B3", 1, 62)
s.ritardando("B3", 7, 9, 44)

# ── TRANSITION: a drumming dominant pedal ──
T = s.section("TRANS")
T.voice("rh").bars(
    "!pp rh [bn3 dn4 g4]q' [bn3 dn4 g4]q' | rh [bn3 dn4 f4]q' [bn3 dn4 f4]q' |"
    " cresc rq [bn3 dn4 ab4]q' [bn3 dn4 ab4]q' [bn3 dn4 ab4]q' |"
    " [bn3 dn4 f4 g4]q' [bn3 dn4 f4 g4]q' [bn3 dn4 f4 ab4]q' !f"
    " [bn3 dn4 f4 bn4]q> |")
T.voice("lh").bars("!pp (g1e. g1s)*4 | (g1e. g1s)*4 | cresc (g1e. g1s)*4 |"
                   " (g1e. g1s)*3 !f [g1 g2]q> |")
s.tempo_change("TRANS", 1, 96)
s.ritardando("TRANS", 1, 5, 116)

# ── C: the march returns, fff ──
C = s.section("C")
crh = [octaves_up(m) if i in (12, 13) else filled(m, c)
       for i, (c, m) in enumerate(MARCH)]
crh[12] = "ped [eb5 g5 bb5 eb6]q.> [dn6 dn7]e [eb6 eb7]e. [f6 f7]s [g5 bb5 eb6 g6]q"
crh[13] = "ped [ab5 c6 eb6 ab6]q.> [g6 g7]e [f6 f7]e. [eb6 eb7]s [ab5 c6 ab6]q lift"
crh[15] = "[g4 bn4 dn5 g5]h> [bn4 dn5 g5]h"
C.voice("rh").bars(join([
    "!f " + crh[0], crh[1], crh[2], crh[3], crh[4], crh[5], crh[6], crh[7],
    "!ff " + crh[8], crh[9], "cresc " + crh[10], crh[11], "!fff " + crh[12],
    crh[13], "dim " + crh[14], "!f " + crh[15]]))
clh = [march_bass(c, ">") for c, _m in MARCH]
clh[0] = "!f " + clh[0]
clh[8] = "!ff " + clh[8]
clh[10] = "cresc " + clh[10]
clh[12] = "!fff [eb1 eb2]q> [bb1 bb2]q' [eb1 eb2]q> [bb1 bb2]q'"
clh[13] = "[ab1 ab2]q> [eb2 eb3]q' [ab1 ab2]q> [eb2 eb3]q'"
clh[14] = "dim " + clh[14]
clh[15] = "!f [g1 g2]h> [g1 g2]h"
C.voice("lh").bars(join(clh))
s.tempo_change("C", 1, 116)

# ── CODA: the march recedes ──
D = s.section("CODA")
D.voice("rh").bars(
    "!p [eb4 g4]q. [eb4 g4]e [eb4 g4]e. [eb4 g4]s [eb4 g4]q |"
    " [dn4 f4]q. [dn4 f4]e [dn4 f4]e. [dn4 f4]s [dn4 f4]q |"
    " dim [c4 eb4]q. [c4 eb4]e [c4 eb4]e. [c4 eb4]s [c4 eb4]q |"
    " [bn3 dn4]h [bn3 f4]h | !pp g4h. f4q | eb4h dn4h |"
    " {c4 eb4 g4 c5 eb5 g5}q {c6 eb6 g6 c7}h. |"
    " !ppp [c4 eb4 g4 c5]w^ |")
D.voice("lh").bars(
    "!p [c2 c3]q' [g1 g2]q' [c2 c3]q' [g1 g2]q' |"
    " [ab1 ab2]q' [f1 f2]q' [ab1 ab2]q' [f1 f2]q' |"
    " dim [g1 g2]q' [dn2 dn3]q' [g1 g2]q' [dn2 dn3]q' |"
    " [g1 g2]q' rq [g1 g2]q' rq | !pp [c2 g2]w | [ab1 f2]h [g1 f2]h |"
    " [c1 c2]w | !ppp [c1 g1 c2]w^ |")
D.soft()
D.pedal("bar")
s.tempo_change("CODA", 1, 100)
s.ritardando("CODA", 3, 9, 50)

s.arrange("A B B3 TRANS C CODA")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "rachmaninoff_prelude_alla_marcia.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
