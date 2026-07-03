#!/usr/bin/env python3
"""Orrery.
Process piece, 140 beats at 60 bpm. Five voices orbit with mutually
prime periods (5, 7, 11, 13, 17 beats); pitches are drawn from the
overtone series of A1 (partials 1-14, equal-tempered). Alignments never
recur within the piece; voices fall silent as their orbits run out,
leaving the fundamental. No meter, theme, or functional harmony."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

T = 140  # total beats: one unmetered span validated as a single bar

# orbital cells — each sums exactly to its period in beats
MERCURY = "e5e' re f5e' re g5q' rh"                       # 5  (partials 12,13,14)
VENUS   = "c#5q_ rq d#5q_ rq b4q_ rh"                     # 7  (10,11,9)
MARS    = "g4h_ rq e4q a4h_ rq g4q rh rq"                 # 11 (7,6,8)
SUN     = "[a1 a2]w~ [a1 a2]w~ [a1 a2]w~ [a1 a2]q"        # 13 (1,2)
NEPTUNE = "e3w~ e3q rq a3h. rh rh rh rh"                  # 17 (3,4)


def orbit(cell, period, dyn_plan):
    """Repeat a cell to fill T beats, padding the tail with rests;
    dyn_plan maps repetition index -> dynamic token."""
    reps = T // period
    parts = []
    for i in range(reps):
        if i in dyn_plan:
            parts.append(dyn_plan[i])
        parts.append(cell)
    pad = T - reps * period
    parts += ["rw"] * int(pad // 4)
    rem = pad % 4
    if rem >= 2:
        parts.append("rh")
        rem -= 2
    if rem >= 1:
        parts.append("rq")
    return " ".join(parts) + " |"


s = Song(tempo=60, time=f"{T}/4", key="A", humanize=2, expressive=False)

orb = s.section("ORBITS")
orb.voice("mercury", vel=34).bars(
    orbit(MERCURY, 5, {0: "!pp", 11: "!p", 19: "!mp", 24: "!pp"}))
orb.voice("venus", vel=36).bars(
    orbit(VENUS, 7, {0: "!pp", 8: "!p", 14: "!mp", 17: "!pp"}))
orb.voice("mars", vel=38).bars(
    orbit(MARS, 11, {0: "!p", 5: "!mp", 10: "!p"}))
orb.voice("sun", vel=42).bars(
    orbit(SUN, 13, {0: "!mp"}))
orb.voice("neptune", vel=36).bars(
    orbit(NEPTUNE, 17, {0: "!p"}))

coda = s.section("LAST", time="4/4")
coda.voice("sun", vel=34).bars("[a1 a2]w^ |")

s.arrange("ORBITS LAST")
s.describe()
s.lint()
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "orrery.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
