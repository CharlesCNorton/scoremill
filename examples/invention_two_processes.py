#!/usr/bin/env python3
"""Invention for Two Processes.
Two-voice invention in C major. All material derives from a single
one-bar subject via shift (sequence and answer), invert (mirror), and
stretch (augmentation). Counterpoint verified with lint()."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, shift, invert, stretch

# the entire melodic material of the piece:
S = "c4s d4s e4s f4s g4e c5e b4s a4s b4s c5s d5e g4e"   # subject (1 bar)
CS = "c3e g3e e3e g3e c4e g3e e3e c3e"                  # countersubject
S_HALF = "c4s d4s e4s f4s g4e c5e"                      # subject head

s = Song(tempo=88, time="4/4", key="C", humanize=1)

inv = s.section("INV")
rh = inv.voice("rh", vel=52)
rh.bars(
    f"!mp {S} | {shift(CS, 7)} | {shift(S, 1)} |"
    " e5s d5s c5s d5s e5e g5e f5s e5s d5s c5s d5q |"
    f" {invert(S, axis='g4')} | {shift(invert(S, axis='g4'), -1)} |"
    f" !mf {S} |"
    " c5s d5s e5s f5s g5e e5e f5s d5s b4s d5s c5q |"
    " [e4 g4 c5]w^& |")
lh = inv.voice("lh", vel=42)
lh.bars(
    f"rw | {shift(S, -7)} | {CS} | {shift(CS, 1)} |"
    f" {shift(CS, -1)} |"
    " f2e c3e a2e c3e f2e a2e c3e f3e |"
    f" {shift(stretch(S_HALF, 2), -5)} |"
    " g2e g3e b3e d4e g3q g2q |"
    " [c2 g2 c3]w^ |")

s.arrange("INV")
s.describe()
s.lint()
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "invention_two_processes.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
