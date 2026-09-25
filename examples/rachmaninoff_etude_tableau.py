#!/usr/bin/env python3
"""Etude-Tableau in E-flat minor, Appassionato. In the manner of
Rachmaninoff.

A sonata-shaped study: a surging theme in octave chords over rolling
triplet arpeggios; a cantabile second theme in the relative major over a
line-cliche bass, joined by an alto line; a development that sequences
the motif up by minor thirds through four keys (chromatic transpose()),
breaks into bell chords over a bass falling to the bottom A of the
keyboard, holds, and drives a dominant pedal with the motif in the bass;
the recapitulation in full chords over the deep arpeggios; and a coda of
bells receding under the soft pedal.

Written in D minor, where the notation is plainest, and moved to E-flat
minor at the end with song.transpose(1)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, chord_pitches, transpose

LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
ACCS = {"#": 1, "b": -1, "n": 0, "##": 2, "bb": -2}
NAMES = ["cn", "c#", "dn", "eb", "en", "fn", "f#", "gn", "g#", "an", "bb", "bn"]
NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.{0,2})?([~>'_^&]*)$")
DUR = {"s": 0.25, "e": 0.5, "e.": 0.75, "q": 1, "q.": 1.5, "h": 2, "h.": 3, "w": 4}


def midi(l, a, o):
    """Pitch of a written note in D minor (a plain b is B-flat)."""
    alter = ACCS[a] if a else (-1 if l == "b" else 0)
    return 12 * (int(o) + 1) + LETTER[l] + alter


def nm(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def below(m, symbol, gap=3):
    pcs = {p % 12 for p in chord_pitches(symbol)}
    return next(p for p in range(m - gap, m - 13, -1) if p % 12 in pcs)


def chords_over(frag, h1, h2, full=False):
    """A bar of melody as octave chords: each note with its octave below,
    and on quarters and longer the chord tone under it (two with
    `full`), from h1 in the first half of the bar and h2 in the second."""
    out, pos = [], 0.0
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        p = midi(*m.group(1, 2, 3))
        d = m.group(4)
        h = h1 if pos < 2 - 1e-9 else h2
        tones = [p - 12, p]
        if DUR[d] >= 1:
            inner = below(p, h)
            tones.append(inner)
            if full:
                tones.append(below(inner, h))
        out.append("[" + " ".join(map(nm, sorted(set(tones)))) + "]" + d
                   + (m.group(5) or ""))
        pos += DUR[d]
    return " ".join(out)


def octaves_below(frag):
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        p = midi(*m.group(1, 2, 3))
        out.append(f"[{nm(p - 12)} {nm(p)}]{m.group(4) or ''}{m.group(5) or ''}")
    return " ".join(out)


def join(items):
    return " | ".join(items) + " |"


def dyn(items, marks):
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


THEME = ["a4q d5q. e5e f5q", "g5h. f5q", "e5q. d5e c#5q e5q", "d5h. a4q",
         "bb4q g5q. f5e e5q", "g5q. f5e e5q c#5q", "d5q. e5e f5q d6q",
         "d6h c#6h",
         "a5q d6q. e6e f6q", "g6h. f6q", "e6q. d6e c6q bn5q",
         "a5q. g5e bb5q c#6q", "d6h. a5q", "bb5q. a5e g5q bb5q",
         "a5q. f5e d5q bb5q", "a5h g5q e5q"]
A_HARM = [("Dm", "Dm/C"), ("Bb", "Gm/Bb"), ("Em7b5/Bb", "A7"), ("Dm", "Dm"),
          ("Gm", "Gm/F"), ("Em7b5", "A7"), ("Dm/F", "Bb"), ("A7sus4", "A7"),
          ("Dm", "Dm/C"), ("Bb", "Bbm6"), ("F/A", "G#dim7"), ("Gm/Bb", "A7"),
          ("Dm/A", "Bbmaj7"), ("Gm7", "A7b9"), ("Dm", "Gm/D"), ("Dm", "C7")]
ARP = "0 2 3 4 3 2"

s = Song(tempo=88, time="4/4", key="Dm", humanize=1, expressive=True,
         title="Etude-Tableau in E-flat minor", composer="after Rachmaninoff")

# ── A: appassionato ──
A = s.section("A")
A.voice("rh").bars(join(dyn(
    [chords_over(m, *h) for m, h in zip(THEME, A_HARM)],
    {0: "!mf", 4: "cresc", 6: "!f", 7: "dim", 8: "!mf", 9: "cresc",
     12: "!ff", 13: "dim", 15: "!mf"})))
lh = A.voice("lh", vel=46)
lh.harmony(" ".join(a + " " + b for a, b in A_HARM), slots="half", octave=2,
           pattern=ARP, unit=1 / 3)
A.pedal("half")
A.rubato(0.04, phrase=2, shape="arch")

# ── B: cantabile in F ──
SONG = ["c5h. a4q", "a4q. bb4e c5q dn5q", "f5h. en5q", "dn5q. c5e bn4q c5q",
        "f5h. en5q", "dn5q. en5e f5q a5q", "g5h. bb4q", "a4w",
        "dn5h. c5q", "bb4q. c5e dn5q en5q", "en5h. f5q", "g5q. f5e en5q g5q",
        "a5h. dn6q", "db6h. c6q", "bb5q. a5e g5q bb5q", "a5h c#5h"]
B_HARM = ("F F/E F7/Eb Bb/D Bbm/Db F/C G7/B C7 F Am/E Dm Dm/C Gm7/Bb C7 F F"
          " Bb Bbmaj7/A Gm C7 Am Dm Gm7 C7 F/A Bbmaj7 Bbm6 F/C Gm7 C7 F A7")
ALTO = ["(rw |)*8", "f4h. f4q", "g4h g4h", "c5h a4h", "dn5h c5h",
        "c5h f5h", "f5h. f5q", "dn5h en5h", "c5h a4h"]
B = s.section("B")
B.voice("song").bars(join(dyn(SONG, {0: "!p", 4: "cresc", 6: "!mp",
                                     8: "cresc", 12: "!mf", 13: "dim",
                                     15: "!p"})))
B.voice("alto").bars(ALTO[0] + " !pp " + join(ALTO[1:]))
arp_b = B.voice("lh", vel=34)
arp_b.harmony(B_HARM, slots="half", octave=2, pattern=ARP, unit=1 / 3)
B.pedal("half")
B.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("B", 1, 72)
s.ritardando("B", 15, 17, 60)

# ── DEVELOPMENT: the motif through four keys, then the bells ──
D = s.section("DEV")
motif = THEME[0] + " | " + THEME[1]
units = [(0, "Dm Dm/C Bb Gm/Bb"), (3, "Fm Fm/Eb Db Bbm/Db"),
         (6, "G#m G#m/F# E C#m/E"), (9, "Bm Bm/A G Em/G")]
seq = []
for n, _h in units:
    seq += octaves_below(transpose(motif, n, key="Dm")).split(" | ")
bells_rh = ["[dn5 f5 a5 dn6]h> [c#5 en5 a5 c#6]h>",
            "[c5 f5 a5 c6]h> [bn4 dn5 g5 bn5]h>",
            "[bb4 dn5 g5 bb5]h> [a4 c#5 en5 a5]h>",
            "[a4 c#5 en5 g5 a5]w>&^"]
hammer = "{[c#5 en5 g5 bb5] [c#5 en5 g5 bb5] [c#5 en5 g5 bb5]}q*4"
D.voice("rh").bars(join(dyn(
    seq + bells_rh + [hammer] * 4,
    {0: "!mf", 2: "cresc", 4: "!f", 6: "cresc", 8: "!fff", 12: "!f",
     13: "cresc", 15: "!fff"})))
dev_lh = D.voice("lh", vel=56)
dev_lh.harmony(" ".join(h for _n, h in units), slots="half", octave=2,
               pattern=ARP, unit=1 / 3)
dev_lh.bars(
    "!fff [dn1 dn2]h> [c#1 c#2]h> | [c1 c2]h> [bn0 bn1]h> |"
    " [bb0 bb1]h> [a0 a1]h> | [a0 a1 en2]w^ |"
    " !f [a1 a2]q [dn2 dn3]q. [en2 en3]e [f2 f3]q | [g2 g3]h. [f2 f3]q |"
    " cresc [en2 en3]q. [dn2 dn3]e [c#2 c#3]q [en2 en3]q |"
    " !fff [a1 a2]h> [a1 a2]h> |")
D.pedal("half")
s.tempo_change("DEV", 1, 96)
s.ritardando("DEV", 1, 9, 108)
s.tempo_change("DEV", 9, 76)
s.tempo_change("DEV", 13, 100)
s.ritardando("DEV", 13, 17, 112)

# ── RECAPITULATION: the theme in full chords ──
R = s.section("RECAP")
R.voice("rh").bars(join(dyn(
    [chords_over(m, *h, full=True) for m, h in zip(THEME, A_HARM)],
    {0: "!ff", 7: "dim", 8: "!f", 9: "cresc", 12: "!fff", 13: "dim",
     15: "!f"})))
deep = R.voice("lh", vel=64)                 # root position this deep
deep.harmony(" ".join(a.split("/")[0] + " " + b.split("/")[0]
                      for a, b in A_HARM), slots="half",
             octave=1, pattern=ARP, unit=1 / 3)
R.pedal("half")
R.rubato(0.04, phrase=2, shape="arch")
s.tempo_change("RECAP", 1, 84)
s.ritardando("RECAP", 15, 17, 66)

# ── CODA: the bells recede ──
C = s.section("CODA")
C.voice("rh").bars(
    "!p [dn6 f6 a6]w | [dn6 g6 bb6]w | [dn6 f6 a6]w | [c#6 en6 a6]w |"
    " !pp [dn5 f5 a5]w | [dn5 g5 bb5]w | [dn5 f5 a5]w |"
    " [bb4 dn5 g5]h [a4 c#5 en5]h | !ppp [a4 dn5 f5 a5]w&^ | rw |")
C.voice("lh").bars(
    "!mp [a1 a2]q [dn2 dn3]q. [en2 en3]e [f2 f3]q | [g2 g3]h. [f2 f3]q |"
    " [en2 en3]q. [dn2 dn3]e [c#2 c#3]q [en2 en3]q | [a1 a2]w |"
    " !pp [dn2 a2]w | [g1 dn2]w | [dn2 a2]w | [g1 g2]h [a1 a2]h |"
    " !ppp [dn1 a1 dn2]w^ | [dn1 dn2]q rq rh |")
C.pedal("bar")
C.soft()
s.tempo_change("CODA", 1, 66)
s.ritardando("CODA", 5, 11, 40)

s.arrange("A B DEV RECAP CODA")
s.transpose(1)                     # D minor -> E-flat minor
s.describe()
s.lint(mode="homophonic")
print("A section, bar by bar:",
      " ".join(c["chord"] for c in s.chords(per="half")
               if c["section"] == "A")[:400])
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "rachmaninoff_etude_tableau.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
