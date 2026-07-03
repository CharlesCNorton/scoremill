#!/usr/bin/env python3
"""Silver Dollar Saloon.
A frontier dance-hall two-step in the style a saloon "professor" would
have pounded out in the 1880s. What separates this from the rag that
grew out of it is the right hand: no syncopation. The melody sits
squarely on the beat, diatonic and bright, dressed with the honky-tonk
grace-note slides that were the piano player's stock in trade, over a
plain oom-pah bass and I-IV-V harmony. A subdominant trio in C, a
reprise, and the period-correct "shave and a haircut, two bits" to
send the room home.

Notated in 2/4 at a brisk two-step clip.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

# Oom-pah voicings: bass on the beat, triad on the offbeat, bass
# alternating root and fifth. B is natural in both G and C, so only
# the F#s need spelling.
VOICE = {
    "G":   ("g2", "[g3 b3 d4]", "d3"),
    "G7":  ("g2", "[f3 b3 d4]", "d3"),
    "C":   ("c3", "[g3 c4 e4]", "g2"),
    "D7":  ("d3", "[f#3 a3 c4]", "a2"),
    "D":   ("d3", "[f#3 a3 d4]", "a2"),
    "A7":  ("a2", "[g3 c#4 e4]", "e3"),
    "Em":  ("e2", "[g3 b3 e4]", "b2"),
    "F":   ("f2", "[f3 a3 c4]", "c3"),
}


def oompah(chords):
    """Eighth-note oom-pah left hand from one chord per 2/4 bar (or a
    2-tuple for two half-bar chords)."""
    bars = []
    for c in chords:
        if isinstance(c, tuple):
            bars.append(" ".join(f"{VOICE[cc][0]}e {VOICE[cc][1]}e"
                                 for cc in c))
        else:
            b1, ch, b2 = VOICE[c]
            bars.append(f"{b1}e {ch}e {b2}e {ch}e")
    return " | ".join(bars) + " |"


s = Song(tempo=126, time="2/4", key="G", humanize=2, expressive=True)

# ── INTRO (4 bars): a call to the floor ──
I = s.section("Intro")
I.voice("rh", vel=58).bars(
    "!f g4e b4e d5e g5e |"
    " d5e b4e g4q |"
    " a4e c5e +c#5 d5e c5e |"
    " c5e a4e d5q |")
I.voice("lh", vel=52).bars(oompah(["G", "G", "D7", "D7"]))

# ── A STRAIN (16 bars): the tune, on the beat, with slides ──
A_RH = (
    "!mf d5e b4e g4e b4e |"
    " +f#4 g4e a4e b4q |"
    " c5e a4e f#4e a4e |"
    " d5e b4e g4q |"
    " d5e b4e g4e b4e |"
    " +f#4 g4e a4e b4q |"
    " d5e e5e d5e c5e |"
    " b4e a4e g4q |"
    " d5e d5e +c#5 d5e e5e |"
    " e5e d5e c5q |"
    " c5e c5e +b4 c5e d5e |"
    " d5e c5e b4q |"
    " d5e b4e g4e b4e |"
    " +f#4 g4e a4e b4q |"
    " a4e c5e f#4e a4e |"
    " g4e b4e g4q |")
A_LH = oompah(["G", "D7", "D7", "G", "G", "D7", "C", "G",
               "D7", "D7", "C", "D7", "G", "D7", "D7", "G"])

A = s.section("A")
A.voice("rh", vel=60).bars(A_RH)
A.voice("lh", vel=50).bars(A_LH)

# ── TRIO (16 bars): warmer, in the subdominant C ──
T_RH = (
    "!mf g4e c5e e5e g5e |"
    " +d5 e5e d5e c5q |"
    " f5e e5e d5e c5e |"
    " e5e c5e g4q |"
    " g4e c5e e5e g5e |"
    " +d5 e5e d5e c5q |"
    " d5e f5e a5e f5e |"
    " e5e d5e c5q |"
    " a4e c5e f5e c5e |"
    " g4e c5e e5q |"
    " d5e f5e g5e e5e |"
    " d5e b4e c5q |"
    " g4e c5e e5e g5e |"
    " +d5 e5e d5e c5q |"
    " g5e e5e d5e f5e |"
    " e5e c5e c5q |")
T_LH = oompah(["C", "C", "G7", "C", "C", "C", "D7", "G7",
               "F", "C", "G7", "C", "C", "G7", "G7", "C"])

T = s.section("Trio", key="C")
T.voice("rh", vel=56).bars(T_RH)
T.voice("lh", vel=48).bars(T_LH)

# ── TAG (2 bars): shave and a haircut, two bits ──
G = s.section("Tag")
G.voice("rh", vel=64).bars("!f g5e d5e d5e e5e | d5e f#5e [g5 b5 d6]q^ |")
G.voice("lh", vel=56).bars(oompah(["G", ("D7", "G")]))

s.arrange("Intro A A Trio Trio A Tag")

s.describe()
s.lint(mode="homophonic")           # melody over oom-pah is homophonic
rep = s.report()
print(f"duration {rep['duration_s']}s, "
      f"collisions {len(s.lint(quiet=True, mode='homophonic'))}")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "silver_dollar_saloon.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
