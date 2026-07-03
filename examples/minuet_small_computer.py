#!/usr/bin/env python3
"""Minuet for a Small Computer.
G major, 3/4. Form: A A B A. Melody over waltz accompaniment."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

s = Song(tempo=104, time="3/4", key="G")

A = s.section("A")
A.voice("rh", vel=52).bars(
    "!mp g4q b4 d5 | d5q. c5e b4q | a4q c5 e5 | d5h. |"
    " e5q d5 c5 | b4q a4 g4 | b4q a4 f#4 | g4h. |")
A.voice("lh", vel=34).harmony(
    "G G Am D7 C G D7 G", style="waltz")

B = s.section("B")
B.voice("rh", vel=52).bars(
    "!mf d5q e5 f#5 | g5q f#5 e5 | d5q c5 b4 | a4h. |"
    " b4q c5 d5 | e5q c5 a4 | g4q b4 a4 | g4h. |")
B.voice("lh", vel=34).harmony(
    "D G D7 D G Am D7 G", style="waltz")

s.arrange("A A B A")
s.describe()
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "minuet_small_computer.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
