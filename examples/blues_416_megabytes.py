#!/usr/bin/env python3
"""Blues for 416 Megabytes.
Twelve-bar blues in C, swing 0.64. Grace-note approaches to blue
thirds, stride accompaniment, four-bar phrase rubato."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

s = Song(tempo=100, time="4/4", key="C", swing=0.64, humanize=2)

A = s.section("A")
A.voice("rh", vel=56).bars(
    "!mf +eb5 e5q g5e a5e bb5e a5e g5e e5e |"
    " c5q re g4e bb4e c5e d5s eb5s d5e |"
    " +f#4 g4q bb4e g4e +eb5 e5q c5q |"
    " c5e bb4 g4 e4 c4q rq |"
    " f4e a4 c5 eb5 d5q c5q |"
    " +e5 f5q d5e bb4e c5h |"
    " +eb5 e5q g5e e5e c5e g4e a4e bb4e |"
    " a4e g4 e4 c4 d4q e4e g4e |"
    " g5q g5e f5e d5e b4e g4q |"
    " f5q f5e eb5e c5e a4e f4q |"
    " +eb5 e5q c5e g4e bb4q a4e g4e |"
    " g4e f#4 g4 b4 c5q' [c4 e4 g4 c5]q^ |")
A.voice("lh", vel=38).harmony(
    "C C C C7 F F C C G7 F C C7", style="stride")
A.rubato(0.03, phrase=4)

A2 = A.variant("A2", vel_scale=0.88)
s.arrange("A A2")
s.describe()
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "blues_416_megabytes.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
