#!/usr/bin/env python3
"""Saltarello alla Chico.
The demo score. A minor, 6/8, quarter = 168. A jumping staccato tune
over an oom-pah left hand, grace-note pickups, pistol-finger accents,
a cadential trill, an echo variant, and a Picardy coda in A major that
accelerates through a sixteenth run to one last plink at the top of
the keyboard. Spirited throughout; dignity nowhere.

lint() reports parallel octaves and fifths between tune and oom-pah.
They are retained deliberately: melody doubling the harmony on strong
beats is the novelty-piano idiom. The linter is advisory; the one
physical collision it found during composition (both hands striking
the same key) was fixed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song


def om(bass, chord, alt):
    """One 6/8 bar of staccato oom-pah: bass, two chords, alt bass."""
    return f"{bass}e' {chord}e' {chord}e' {alt}e' {chord}e' {chord}e'"


AM, E7, DM = "[e3 a3 c4]", "[e3 g#3 d4]", "[f3 a3 d4]"
C, F, G7 = "[e3 g3 c4]", "[f3 a3 c4]", "[f3 g3 b3]"

s = Song(tempo=168, time="6/8", key="Am", humanize=1, expressive=True)

# ── INTRO: the vamp alone, curtain up ──
intro = s.section("INTRO")
intro.voice("lh", vel=42).bars(
    "!mf " + om("a2", AM, "e2") + " | " + om("a2", AM, "e2") + " |")

# ── A: the jump tune (saltare: to jump) ──
A = s.section("A")
A.voice("rh", vel=54).bars(
    "!mf e5e' a5e' c6e' b5e' a5e' g5e' |"
    " +g#5 a5q.' e5q.' |"
    " f5e' a5e' d6e' c6e' a5e' f5e' |"
    " +c#6 d6q.' a5q.' |"
    " c6e' b5e' a5e' g#5e' a5e' b5e' |"
    " c6e' a5e' e5e' c5q.' |"
    " d5e' e5e' f5e' e5e' d5e' b4e' |"
    " +g#4 a4q. a5e'> rq |")
A.voice("lh", vel=42).bars(
    "!mf "
    + " | ".join([om("a2", AM, "e2"), om("a2", AM, "e2"),
                  om("d3", DM, "a2"), om("d3", DM, "a2"),
                  om("e2", E7, "b2"), om("a2", AM, "e2"),
                  om("e2", E7, "b2")])
    + " | a2e' " + AM + "e' " + AM + "e' a2e'> re re |")

# ── A2: the echo, same jokes told softer ──
A2 = A.variant("A2", vel_scale=0.85)

# ── B: relative major, the grin ──
B = s.section("B")
B.voice("rh", vel=56).bars(
    "!f g5e' e5e' c5e' g5e' e5e' c5e' |"
    " +f#5 g5q.' e6e'> re re |"
    " a5e' f5e' c5e' a5e' f5e' c5e' |"
    " +b5 c6q.' g6e'> re re |"
    " g5e' a5e' b5e' c6e' d6e' e6e' |"
    " f6e' d6e' b5e' g5e' f5e' d5e' |"
    " e5e' g5e' c6e' g5e' e5e' c5e' |"
    " d5q.% c5q.' |")
B.voice("lh", vel=44).bars(
    "!mf "
    + " | ".join([om("c3", C, "g2"), om("c3", C, "g2"),
                  om("f2", F, "c3"), om("c3", C, "g2"),
                  om("g2", G7, "d3"), om("g2", G7, "d3"),
                  om("c3", C, "g2")])
    + " | g2e' " + G7 + "e' " + G7 + "e' c3q.' |")

# ── CODA: Picardy turn to A major, accelerando, run, plink ──
# (section key "A": plain c, f, g sound sharp via the signature)
coda = s.section("CODA", key="A")
coda.voice("rh", vel=56).bars(
    "!f a4e' c5e' e5e' a5e' c6e' e6e' |"
    " e6e' d6e' c6e' b5e' a5e' g5e' |"
    " a5e' e5e' c5e' a4e' e4e' d4e' |"
    " cresc b3s c4s d4s e4s f4s g4s a4s b4s c5s d5s e5s f5s |"
    " !ff +g5 [a3 e4 a4 c5 e5]h.^& |"
    " a6q.'> rq. |")
coda.voice("lh", vel=44).bars(
    "!f "
    + " | ".join([om("a2", AM, "e2"), om("a2", AM, "e2"),
                  om("a2", AM, "e2")])
    + " | e2q.' [e3 g3 d4]q.' |"
    " [a1 e2 a2]h.^& |"
    " a1q.'> rq. |")
s.ritardando("CODA", 1, 4, 208)      # a faster target: accelerando

s.arrange("INTRO A A2 B A CODA")

s.describe()
s.lint()
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "saltarello_alla_chico.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
