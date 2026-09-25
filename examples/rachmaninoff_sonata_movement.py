#!/usr/bin/env python3
"""Sonata in B-flat minor, first movement (Allegro agitato). In the
manner of Rachmaninoff.

After the Second Sonata: an arpeggio cascade from the top of the
keyboard to a bell at the bottom; an agitated first theme, a chromatic
line cliche in octave chords over triplet surges; bell chords turning to
the relative major and held; a broad second theme whose minor-iv sigh
(A to A-flat) recurs, joined by an alto countermelody; a quiet closing
group with the first theme murmuring in the bass; a development that
climbs the motif by whole steps through four keys (chromatic
transpose()), rings bells over a chromatic bass falling to the lowest A,
and holds; a dominant pedal; the recapitulation, the second theme
returning grandioso in the major; and a Piu mosso coda, the motif in
augmentation over a whirlwind, contrary chromatic octaves, and the
short-short-long cadence.

Written in A minor, where the notation is plainest, and moved to
B-flat minor at the end with song.transpose(1)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, chord_pitches, transpose

LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
ACCS = {"#": 1, "b": -1, "n": 0, "##": 2, "bb": -2}
NAMES = ["cn", "c#", "dn", "d#", "en", "fn", "f#", "gn", "g#", "an", "a#", "bn"]
NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.{0,2})?([~>'_^&]*)$")
DUR = {"t": 0.125, "s": 0.25, "e": 0.5, "e.": 0.75, "q": 1, "q.": 1.5,
       "h": 2, "h.": 3, "w": 4}


def midi(l, a, o):
    return 12 * (int(o) + 1) + LETTER[l] + ACCS.get(a or "n", 0)


def nm(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def below(m, symbol, gap=3):
    pcs = {p % 12 for p in chord_pitches(symbol)}
    return next(p for p in range(m - gap, m - 13, -1) if p % 12 in pcs)


def chords_over(frag, h1, h2, full=False):
    """Melody as octave chords, the chord tone (two with `full`) under
    each quarter or longer, from h1 in the first half bar, h2 after."""
    out, pos = [], 0.0
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        p, d = midi(*m.group(1, 2, 3)), m.group(4)
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


def octaves(frag, up=False):
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        p = midi(*m.group(1, 2, 3))
        lo, hi = (p, p + 12) if up else (p - 12, p)
        out.append(f"[{nm(lo)} {nm(hi)}]{m.group(4) or ''}{m.group(5) or ''}")
    return " ".join(out)


def join(items):
    return " | ".join(items) + " |"


def dyn(items, marks):
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


def pairs(h):
    return list(zip(h[0::2], h[1::2]))


ARP = "0 2 3 4 3 2"
T1 = ["a5q. g#5e g5q f#5q", "f5h e5h", "c6q. b5e bb5q a5q", "g#5h e5h",
      "d6q. c#6e c6q b5q", "bb5h a5h", "f6q. e6e d6q c6q", "b5h e5h",
      "a5q. g#5e g5q f#5q", "f5h e5h", "c6q. b5e bb5q a5q", "g#5h b5h",
      "c6q. d6e e6q f6q", "f6q. e6e d6q a5q", "bb5h g#5h", "a5w"]
T1H = ["Am", "Am", "Dm/F", "E", "F", "F", "E7", "E7", "Dm", "Dm", "Bb", "Am",
       "Dm/F", "Dm/F", "E7", "E7", "Am", "Am", "Dm/F", "E", "F", "F", "E7",
       "E7", "Am/C", "Am/C", "Dm", "Dm/F", "Bb", "E7", "Am", "Am"]
T2 = ["e4q c5h.", "b4q. a4e a4h", "a4q. c5e f5q. e5e", "d5h. b4q",
      "g4q e5h.", "d5q. c5e c5h", "c5q. a4e ab4h", "g4w",
      "e5q g5h.", "a5q. g5e f5q. ab5e", "g5h. c#6q", "d6q. c6e a5h",
      "f5q. e5e d5q. b4e", "c5h. f5q", "e5q. d5e d5h", "c5w^"]
T2H = ["C", "C/B", "Am", "Am/G", "F", "Dm7", "G7sus4", "G7", "C/E", "C",
       "Am", "Am/G", "F", "Fm6", "C/G", "G7", "C", "C7/Bb", "F/A", "Fm/Ab",
       "C/G", "A7", "Dm", "Dm/C", "G7/B", "G7", "C/E", "F", "C/G", "G7",
       "C", "C"]
ALTO = ["c5h bb4h", "c5h c5h", "e5h e5h", "f5h f5h", "d5h g4h", "g4h a4h",
        "g4h f4h", "e4w^"]

s = Song(tempo=104, time="4/4", key="Am", humanize=1, expressive=True,
         title="Sonata in B-flat minor, first movement",
         composer="after Rachmaninoff")

# ── CASCADE ──
cascade = " ".join(nm(p) + "t" for p in
                   (100, 96, 93, 88, 84, 81, 76, 72, 69, 64, 60, 57, 52, 48,
                    45, 40))
K = s.section("CASCADE")
K.voice("rh").bars("!ff " + cascade + " rh | [e4 a4 c5 e5]q> [e4 a4 c5 e5]q>"
                   " [e4 g#4 b4 e5]h> |")
K.voice("lh").bars("!ff rh [a0 a1 e2 a2]h> | [a1 a2]q [a1 a2]q [e1 e2]h |")
K.pedal("half")

# ── FIRST THEME ──
A1 = s.section("T1")
A1.voice("rh").bars(join(dyn([chords_over(m, *h) for m, h in zip(T1, pairs(T1H))],
                             {0: "!f", 2: "cresc", 4: "!ff", 6: "dim", 7: "!f",
                              10: "cresc", 12: "!ff", 14: "dim", 15: "!mf"})))
A1.voice("lh", vel=58).harmony(" ".join(T1H), slots="half", octave=2,
                               pattern=ARP, unit=1 / 3)
A1.pedal("half")
A1.rubato(0.03, phrase=2, shape="arch")

# ── BELLS: toward the relative major ──
B = s.section("BELLS")
B.voice("rh").bars(
    "!ff [e4 a4 c5 e5]q> [e4 a4 c5 e5]q> [f4 a4 d5 f5]q> [f4 a4 d5 f5]q> |"
    " [e4 g#4 b4 e5]h> [e4 a4 c5 e5]h> |"
    " cresc [g4 c5 e5 g5]q> [g4 c5 e5 g5]q> [g4 b4 d5 g5]q> [g4 b4 d5 g5]q> |"
    " !fff [g4 b4 d5 f5 g5]h.>&^ rq |")
B.voice("lh").bars("!ff [a1 a2]h [d1 d2]h | [e1 e2]h [a1 a2]h |"
                   " cresc [c2 c3]h [g1 g2]h | !fff [g1 g2]h.^ rq |")
B.pedal("half")
s.tempo_change("BELLS", 1, 100)
s.ritardando("BELLS", 3, 5, 76)

# ── SECOND THEME, C major ──
S2 = s.section("T2", key="C")
S2.voice("song").bars(join(dyn(T2, {0: "!p", 8: "cresc", 11: "!mf",
                                    12: "dim", 15: "!p"})))
S2.voice("alto").bars("(rw |)*8 !pp " + join(ALTO))
S2.voice("lh", vel=32).harmony(" ".join(T2H), slots="half", octave=2,
                               pattern=ARP, unit=1 / 3)
S2.pedal("half")
S2.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("T2", 1, 66)
s.ritardando("T2", 15, 17, 52)

# ── CLOSING: bells, the first theme murmuring below ──
CL = s.section("CLOSING", key="C")
CL.voice("rh").bars(
    "!pp [e5 g5 c6]w& | [e5 a5 c6]h [dn5 g#5 bn5]h | [e5 g5 c6]w& |"
    " [c5 f5 a5]h [bn4 e5 g#5]h | [c5 e5 a5]w& | [c5 e5 g5]h [bn4 dn5 g5]h |"
    " [c5 e5 g5 c6]w& | !ppp [c5 e5 g5 c6]w^ |")
CL.voice("lh").bars(
    "!p [a2 a3]q. [g#2 g#3]e [g2 g3]q [f#2 f#3]q | [f2 f3]h [e2 e3]h |"
    " [a2 a3]q. [g#2 g#3]e [g2 g3]q [f#2 f#3]q | [f2 f3]h [e2 e3]h |"
    " !pp [a1 a2]w | [g1 g2]w | [c2 c3]w | !ppp [c1 c2]w^ |")
CL.pedal("half")
CL.soft()
s.tempo_change("CLOSING", 1, 60)
s.ritardando("CLOSING", 5, 9, 44)

# ── DEVELOPMENT ──
D = s.section("DEV")
units = [(0, "Am Am Dm/F E"), (2, "Bm Bm Em/G F#"), (4, "C#m C#m F#m/A G#"),
         (6, "D#m D#m G#m/B A#")]
seq = []
for n, _h in units:
    seq += octaves(transpose(T1[0] + " | " + T1[1], n, key="Am")).split(" | ")
bells = ["[d#5 f#5 an5 d#6]h> [dn5 fn5 g#5 dn6]h>",
         "[c#5 en5 gn5 c#6]h> [cn5 d#5 f#5 cn6]h>",
         "[bn4 dn5 fn5 bn5]h> [a#4 dn5 fn5 a#5]h>",
         "[an4 cn5 en5 an5]h> [g#4 bn4 dn5 en5 g#5]h>^"]
hammer = "{[bn4 dn5 en5 g#5] [bn4 dn5 en5 g#5] [bn4 dn5 en5 g#5]}q*4"
D.voice("rh").bars(join(dyn(seq + bells + [hammer] * 4,
                            {0: "!f", 2: "cresc", 6: "!ff", 8: "!fff",
                             12: "!f", 13: "cresc", 15: "!fff"})))
dev = D.voice("lh", vel=60)
dev.harmony(" ".join(h for _n, h in units), slots="half", octave=2,
            pattern=ARP, unit=1 / 3)
dev.bars(
    "!fff [d#1 d#2]h> [dn1 dn2]h> | [c#1 c#2]h> [cn1 cn2]h> |"
    " [bn0 bn1]h> [a#0 a#1]h> | [an0 an1]h> [en1 en2]h>^ |"
    " !f [a1 a2]q. [g#1 g#2]e [g1 g2]q [f#1 f#2]q | [f1 f2]h [e1 e2]h |"
    " cresc [a1 a2]q. [g#1 g#2]e [g1 g2]q [f#1 f#2]q | !fff [f1 f2]h [e1 e2]h |")
D.pedal("half")
s.tempo_change("DEV", 1, 108)
s.ritardando("DEV", 1, 9, 116)
s.tempo_change("DEV", 9, 84)
s.tempo_change("DEV", 13, 104)
s.ritardando("DEV", 13, 17, 120)

# ── RECAPITULATION ──
R1 = s.section("RECAP1")
R1.voice("rh").bars(join(dyn(
    [chords_over(m, *h, full=True) for m, h in zip(T1[:8], pairs(T1H[:16]))],
    {0: "!ff", 6: "dim", 7: "!f"})))
R1.voice("lh", vel=66).harmony(" ".join(T1H[:16]), slots="half", octave=2,
                               pattern=ARP, unit=1 / 3)
R1.pedal("half")
s.tempo_change("RECAP1", 1, 108)

T2A = [transpose(m, -3, key="C") for m in T2]
T2H_A = ["A", "A/G#", "F#m", "F#m/E", "D", "Bm7", "E7sus4", "E7", "A/C#", "A",
         "F#m", "F#m/E", "D", "Dm6", "A/E", "E7", "A", "A7/G", "D/F#", "Dm/F",
         "A/E", "F#7", "Bm", "Bm/A", "E7/G#", "E7", "A/C#", "D", "A/E", "E7",
         "A", "A"]
R2 = s.section("RECAP2", key="A")
R2.voice("song").bars(join(dyn([octaves(m, up=True) for m in T2A],
                               {0: "!f", 8: "cresc", 11: "!ff", 12: "dim",
                                15: "!f"})))
R2.voice("alto").bars("(rw |)*8 !mf " + join(transpose(a, -3, key="C")
                                              for a in ALTO))
R2.voice("lh", vel=54).harmony(" ".join(T2H_A), slots="half", octave=2,
                               pattern="0 1 2 3 2 1", unit=1 / 3)
R2.pedal("half")
R2.rubato(0.04, phrase=2, shape="cradle")
s.tempo_change("RECAP2", 1, 72)
s.ritardando("RECAP2", 15, 17, 56)

# ── CODA: Piu mosso ──
up = " ".join(f"[{nm(p)} {nm(p + 12)}]s" for p in range(76, 92))
down = " ".join(f"[{nm(p - 12)} {nm(p)}]s" for p in range(52, 36, -1))
C = s.section("CODA")
C.voice("rh").bars(
    "!f [a4 a5]h [g#4 g#5]h | [g4 g5]h [f#4 f#5]h | cresc [f4 f5]h [e4 e5]h |"
    " [e4 g#4 b4 e5]w | !fff " + up + " |"
    " [a4 c5 e5 a5]q> [e4 g#4 b4 e5]q> [a4 c5 e5 a5]q> [e4 g#4 b4 e5]q> |"
    " [a4 c5 e5 a5]q> [a4 c5 e5 a5]q> [e4 g#4 b4 dn5 e5]q> [e4 g#4 b4 dn5 e5]q> |"
    " [a4 c5 e5 a5]e> [e4 g#4 b4 e5]e> [a3 e4 a4 c5 e5 a5]q>& rh |")
whirl = C.voice("lh", vel=62)
whirl.harmony("Am Am/G# Am/G D7/F# Dm/F E7 E7 E7", slots="half", octave=2,
              pattern=ARP, unit=1 / 3)
whirl.bars(
    "!fff " + down + " | [a1 a2]q [e1 e2]q [a1 a2]q [e1 e2]q |"
    " [a1 a2]q [a1 a2]q [e1 e2]q [e1 e2]q |"
    " [a1 a2]e> [e1 e2]e> [a0 a1 e2 a2]q> rh |")
C.pedal(1)
s.tempo_change("CODA", 1, 120)
s.ritardando("CODA", 1, 7, 132)
s.tempo_change("CODA", 8, 104)

s.arrange("CASCADE T1 BELLS T2 CLOSING DEV RECAP1 RECAP2 CODA")
s.transpose(1)                         # A minor -> B-flat minor
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "rachmaninoff_sonata_movement.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
