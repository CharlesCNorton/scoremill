#!/usr/bin/env python3
"""Prelude in D minor, "The Bells". In the manner of Rachmaninoff.

A bell motto (A-G-D) struck in fortissimo octaves; a hushed chorale over
a descending lament bass; an agitato middle section of rolling triplet
arpeggios under a melody in octaves; the motto returned in fff chords;
a coda that sinks to ppp under the soft pedal."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

s = Song(tempo=56, time="4/4", key="Dm", humanize=1, expressive=True)


def wave(p):
    """One bar of rolling triplet eighths over six chord tones, low to
    high: up through all six, then back down."""
    return (f"{{{p[0]} {p[1]} {p[2]}}}q {{{p[3]} {p[4]} {p[5]}}}q "
            f"{{{p[4]} {p[3]} {p[2]}}}q {{{p[3]} {p[2]} {p[1]}}}q")


# ── INTRO: the bells ──
intro = s.section("INTRO")
intro.voice("rh").bars("!ff [a4 a5]h> [g4 g5]h> | [d4 f4 a4 d5]w& |")
intro.voice("lh").bars("!ff [a1 a2]h> [g1 g2]h> | [d1 a1 d2]w |")
intro.pedal("half")
s.tempo_change("INTRO", 2, 44)

# ── A: chorale over a lament bass ──
A = s.section("A")
A.voice("rh").bars(
    "!p [d4 f4 a4]q [bb3 d4 g4]q [f3 a3 d4]h |"
    " [bb3 c4 e4]q [a3 c4 f4]q [bb3 d4 g4]q [c#4 e4 a4]q |"
    " [d4 g4 bb4]q [d4 f4 a4]q [bb3 e4 g4]q [a3 d4 f4]q |"
    " [a3 c#4 e4]h [c#4 e4 g4 a4]h |"
    " cresc [d4 f4 a4]q [bb3 d4 g4]q [f4 a4 d5]h |"
    " !mf [e4 g4 c5]q [d4 g4 bb4]q dim [d4 f4 a4]q [c#4 e4 g4]q |"
    " [a3 d4 f4]q [a3 c#4 e4]q [f3 a3 d4]q [e3 g3 a3 c#4]q |"
    " !pp [f3 a3 d4]w |")
A.voice("lh").bars(
    "!p [d2 d3]w |"
    " [c2 c3]h [bb1 bb2]q [a1 a2]q |"
    " [g1 g2]q [f1 f2]q [e1 e2]q [d1 d2]q |"
    " [a1 a2]w |"
    " cresc [d2 d3]h [bb1 bb2]h |"
    " !mf [bb1 bb2]q [g1 g2]q dim [f1 f2]q [e1 e2]q |"
    " [a1 a2]w |"
    " !pp [d1 d2]w |")
A.pedal(1)
A.rubato(0.04, phrase=2, shape="arch")

# ── B: agitato ──
B = s.section("B")
B.voice("rh").bars(
    "!mf [a4 a5]q. [g4 g5]e [f4 f5]q [e4 e5]q |"
    " [d5 d6]h [bb4 bb5]q [a4 a5]q |"
    " cresc [g4 g5]q. [f4 f5]e [e4 e5]q [bb4 bb5]q |"
    " [a4 a5]w |"
    " !f [f5 f6]q. [e5 e6]e [d5 d6]q [c5 c6]q |"
    " cresc [d5 d6]q. [c5 c6]e [bn4 bn5]q [g#4 g#5]q |"
    " [a4 a5]q. [bn4 bn5]e [c#5 c#6]q [e5 e6]q |"
    " !ff [g5 g6]h [f5 f6]q [e5 e6]q |")
chords = [
    ["d2", "a2", "d3", "f3", "a3", "d4"],        # Dm
    ["g1", "d2", "g2", "bb2", "d3", "g3"],       # Gm
    ["c2", "g2", "bb2", "e3", "g3", "c4"],       # C7
    ["f1", "c2", "f2", "a2", "c3", "f3"],        # F
    ["bb1", "f2", "bb2", "d3", "f3", "bb3"],     # Bb
    ["e2", "bn2", "d3", "g#3", "bn3", "e4"],     # E7
    ["a1", "e2", "a2", "c#3", "e3", "a3"],       # A
    ["a1", "e2", "g2", "c#3", "e3", "g3"],       # A7
]
lh = [wave(c) for c in chords]
lh[0] = "!mp " + lh[0]
lh[2] = "cresc " + lh[2]
lh[4] = "!f " + lh[4]
lh[5] = "cresc " + lh[5]
lh[7] = "!ff " + lh[7]
B.voice("lh").bars(" | ".join(lh) + " |")
B.pedal("bar")
B.rubato(0.05, phrase=2, shape="arch")
s.tempo_change("B", 1, 96)

# ── RETURN: the bells, fff ──
R = s.section("RETURN")
R.voice("rh").bars(
    "!fff [a4 d5 f5 a5]h> [g4 bb4 d5 g5]h> | [d5 f5 a5 d6]w& |"
    " [a4 c#5 e5 a5]h> [bb4 d5 g5 bb5]h> | [a4 c#5 e5 g5 a5]w& |")
R.voice("lh").bars(
    "!fff [a1 a2]h> [g1 g2]h> | [d1 d2 a2 d3]w& |"
    " [a1 a2]h> [g1 g2]h> | [a1 e2 a2]w |")
R.pedal("half")

# ── CODA: the bells recede ──
C = s.section("CODA")
C.voice("rh").bars(
    "!mp [f4 a4 d5]q [e4 g4 c#5]q [d4 f4 a4]h |"
    " !p a4h g4h |"
    " [f3 a3 d4]w |"
    " !ppp [a3 d4 f4 a4 d5]w& |")
C.voice("lh").bars(
    "!mp [d2 d3]w |"
    " !p [d2 a2 d3]w |"
    " [d2 a2]w |"
    " !ppp [d1 a1 d2]w |")
C.pedal("bar")
C.soft()
s.ritardando("CODA", 2, 4, 38)

s.arrange("INTRO A B RETURN CODA")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "rachmaninoff_prelude_bells.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
