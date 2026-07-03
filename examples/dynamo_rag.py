#!/usr/bin/env python3
"""The Dynamo Rag.
A classic multi-strain piano rag in the Joplin tradition. C major with
the trio in the subdominant F; march form Intro-AA-BB-A-CC. The left
hand walks an eighth-note stride (bass on the beat, chord on the
offbeat, bass alternating root and fifth); the right hand carries the
written syncopation that is the whole point of ragtime. Straight
eighths, no swing, and, as Joplin insisted, never fast.

Notated in 2/4, the ragtime convention, so a "beat" here is a quarter
and the sixteenth runs are the genuine article.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

# Stride voicings: (bass on the beat, chord on the offbeat, alternate
# bass). B naturals are spelled explicitly so these read correctly in
# both the C strains and the F-major trio.
VOICE = {
    "C":   ("c2", "[e3 g3 c4]", "g2"),
    "C7":  ("c2", "[e3 g3 bb3]", "g2"),
    "F":   ("f2", "[a3 c4 f4]", "c3"),
    "Fm":  ("f2", "[ab3 c4 f4]", "c3"),
    "G":   ("g2", "[bn3 d4 g4]", "d3"),
    "G7":  ("g2", "[bn3 d4 f4]", "d3"),
    "D7":  ("d2", "[f#3 a3 c4]", "a2"),
    "A7":  ("a2", "[c#4 e4 g4]", "e3"),
    "Bb":  ("bb2", "[d3 f3 bb3]", "f2"),
    "Am":  ("a2", "[a3 c4 e4]", "e3"),
    "Dm":  ("d2", "[f3 a3 d4]", "a2"),
}


def stride(chords):
    """Render an eighth-note stride left hand from a list of one chord
    per 2/4 bar (or a 2-tuple for two half-bar chords)."""
    bars = []
    for c in chords:
        if isinstance(c, tuple):
            half = []
            for cc in c:
                b1, ch, _ = VOICE[cc]
                half.append(f"{b1}e {ch}e")
            bars.append(" ".join(half))
        else:
            b1, ch, b2 = VOICE[c]
            bars.append(f"{b1}e {ch}e {b2}e {ch}e")
    return " | ".join(bars) + " |"


s = Song(tempo=92, time="2/4", key="C", humanize=1, expressive=True)

# ── INTRO (4 bars): cakewalk thirds into the dominant ──
I = s.section("Intro")
I.voice("rh", vel=54).bars(
    "!mf [e5 g5]e [e5 g5]e [f5 a5]s [e5 g5]s [d5 f5]e |"
    " [e5 g5]e [c5 e5]e g4q |"
    " [d5 f5]e [d5 f5]e [f5 bn5]s [e5 g5]s [d5 f5]e |"
    " [d5 f5]e [bn4 d5]e g4q |")
I.voice("lh", vel=46).bars(stride(["C", "C", "G7", "G7"]))

# ── A STRAIN (16 bars): the hook ──
A_RH = (
    "!mf g4e c5s e5s g5e c5e |"
    " e5s d5e c5s d5e e5e |"
    " g4e c5s e5s g5e e5e |"
    " d5e e5e c5q |"
    " g4e c5s e5s g5e c5e |"
    " e5s d5e c5s d5e e5e |"
    " a5e g5s e5s g5e c5e |"
    " e5e c5e g4q |"
    " a4e c5s f5s a5e c5e |"
    " b4e d5s f5s g5e d5e |"
    " c5e e5s g5s c6e e5e |"
    " d5e bn4e g4q |"
    " g4e c5s e5s g5e c5e |"
    " e5s d5e c5s d5e e5e |"
    " d5e f5s a5s g5e d5e |"
    " c5e e5e c5q |")
A_LH = stride(["C", "C", "C", "G7", "C", "C", "G7", "C",
               "F", "G7", "C", "G7", "C", "C", "G7", "C"])

A = s.section("A")
A.voice("rh", vel=56).bars(A_RH)
A.voice("lh", vel=46).bars(A_LH)

# ── B STRAIN (16 bars): higher, busier, a turn toward A minor ──
B_RH = (
    "!f e5s f5s g5s a5s g5e e5e |"
    " c5e e5s g5s c6e g5e |"
    " a5s bn5s c6s a5s g5e e5e |"
    " a5e g5e e5q |"
    " e5s f5s g5s a5s g5e e5e |"
    " c5e e5s g5s c6e g5e |"
    " d6s c6s bn5s a5s g5e e5e |"
    " c6e g5e e5q |"
    " f5s g5s a5s c6s a5e f5e |"
    " d5e f#5s a5s d6e a5e |"
    " g5s a5s bn5s c6s bn5e g5e |"
    " d6e bn5e g5q |"
    " e5s f5s g5s a5s g5e e5e |"
    " c5e e5s g5s c6e g5e |"
    " d6s c6s bn5s a5s g5e f5e |"
    " e5e c5e c5q |")
B_LH = stride(["C", "C", "Am", "Am", "C", "C", "G7", "C",
               "F", "D7", "G7", "G7", "C", "C", "G7", "C"])

B = s.section("B")
B.voice("rh", vel=58).bars(B_RH)
B.voice("lh", vel=48).bars(B_LH)

# ── TRIO (16 bars): the big tune, in F, warmer and more legato ──
C_RH = (
    "!mf c5e f5e a5e f5e |"
    " g5e f5s e5s f5q |"
    " a5e c6e a5e f5e |"
    " g5h |"
    " c5e f5e a5e c6e |"
    " d6e c6s a5s g5q |"
    " b5e a5e g5e f5e |"
    " a5h |"
    " d5e g5e bn5e g5e |"
    " c6e a5e f5q |"
    " c5e e5e g5e bn5e |"
    " a5e g5e f5q |"
    " c5e f5e a5e f5e |"
    " g5e f5s e5s f5q |"
    " a5e c6e d6e c6e |"
    " c6e a5e f5q |")
C_LH = stride(["F", "C7", "F", "C7", "F", "C7", "F", "F",
               "Bb", "F", "G7", "C7", "F", "C7", ("G7", "C7"), "F"])

T = s.section("Trio", key="F")
T.voice("rh", vel=54).bars(C_RH)
T.voice("lh", vel=46).bars(C_LH)

s.arrange("Intro A A B B A Trio Trio")

s.describe()
# A rag is homophonic: the melody and the stride bass outline the same
# chords, so strict counterpoint flags their parallels by the dozen.
# The honest check for this texture is the collision pass.
s.lint(mode="homophonic")
rep = s.report()
print(f"duration {rep['duration_s']}s, "
      f"collisions {len(s.lint(quiet=True, mode='homophonic'))}")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "dynamo_rag.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
