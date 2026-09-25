#!/usr/bin/env python3
"""Fantasy on Themes from an Imaginary Opera. In the manner of Horowitz.

An operatic paraphrase of the kind Horowitz played after Liszt: a stormy
introduction of diminished-seventh tremolos and an octave cascade, a
general pause, and a recitative that previews the aria in the tenor;
the aria, sung in the middle of the keyboard under a filigree (the
three-hand effect), then sung again in octaves over wide arpeggios and
crowned by a cadenza; a festive chorus, twice; a love duet, the soprano
asking, the baritone answering, then both together; a galop of repeated
notes, plain and then in octaves over a cimbalom bass; and a stretta
that combines the themes, the aria returning in the bass under the
galop's figuration, before a coda of contrary chromatic octaves."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, chord_pitches, transpose

LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
ACCS = {"#": 1, "b": -1, "n": 0, "##": 2, "bb": -2}
NAMES = ["cn", "c#", "dn", "eb", "en", "fn", "f#", "gn", "g#", "an", "bb", "bn"]
NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.{0,2})?([~>'_^&%]*)$")
DUR = {"t": 0.125, "s": 0.25, "e": 0.5, "e.": 0.75, "q": 1, "q.": 1.5,
       "h": 2, "h.": 3, "w": 4}
SPELL = {0.5: "e", 1: "q", 1.5: "q.", 2: "h", 3: "h."}


def midi(l, a, o):
    """Pitch of a written note; every note here carries its accidental,
    so a plain letter is natural."""
    return 12 * (int(o) + 1) + LETTER[l] + ACCS.get(a or "n", 0)


def nm(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def below(m, symbol, gap=3):
    pcs = {p % 12 for p in chord_pitches(symbol)}
    return next(p for p in range(m - gap, m - 13, -1) if p % 12 in pcs)


def voiced(frag, fn, mark=""):
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        d = m.group(4) or ""
        ps = sorted(set(fn(midi(*m.group(1, 2, 3)), d)))
        body = nm(ps[0]) if len(ps) == 1 else "[" + " ".join(map(nm, ps)) + "]"
        out.append(body + d + (m.group(5) or "") + mark)
    return " ".join(out)


def halves(frag):
    """Split a 4/4 bar into two 2/4 bars, tying a note across the middle."""
    first, second, pos = [], [], 0.0
    for tok in frag.split():
        m = NOTE.match(tok)
        d = DUR[m.group(4)]
        name = "".join(x or "" for x in m.group(1, 2, 3))
        if pos + d <= 2 + 1e-9:
            first.append(tok)
        elif pos >= 2 - 1e-9:
            second.append(tok)
        else:
            a, b = 2 - pos, pos + d - 2
            first.append(f"{name}{SPELL[a]}~")
            second.append(f"{name}{SPELL[b]}")
        pos += d
    return " ".join(first), " ".join(second)


def join(items):
    return " | ".join(items) + " |"


def dyn(items, marks):
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


s = Song(tempo=76, time="4/4", key="Dm", humanize=1, expressive=True,
         title="Fantasy on Themes from an Imaginary Opera",
         composer="after Horowitz")

# ── INTRODUZIONE ──
cascade = " ".join(f"[{nm(p - 12)} {nm(p)}]s" for p in
                   (94, 91, 88, 85, 82, 79, 76, 73, 70, 67, 64, 61, 58, 55,
                    52, 49))
I = s.section("INTRO")
I.voice("rh").bars(
    "!p ([c#5 en5]t [gn5 bb5]t)*8 cresc ([c#5 en5]t [gn5 bb5]t)*8 |"
    " !ff " + cascade + " |"
    " [an4 c#5 en5 gn5 an5]h>&^ rh | rw^ |"
    " !mp rh [fn4 an4 cn5]h | rh [dn4 fn4 bb4]h^ |"
    " !p rh [en4 gn4 bb4 cn5]h | [en4 gn4 bb4 cn5]w&^ |")
I.voice("lh").bars(
    "!p [dn1 dn2]w | !ff [dn1 dn2]q> rq rh | [an0 an1]h>^ rh | rw^ |"
    " !mp [cn3 cn4]q. [dn3 dn4]e [cn3 cn4]q [an2 an3]q | [bb2 bb3]h^ rh |"
    " !p [cn3 cn4]q. [dn3 dn4]e [cn3 cn4]q [fn3 fn4]q | [cn3 cn4]w^ |")
I.pedal("bar")
s.tempo_change("INTRO", 5, 58)

# ── ARIA: the voice in the middle, filigree above ──
ARIA = ["c5q. d5e c5q a4q", "d5h c5q. bb4e", "a4q. bb4e c5q f5q", "e5h. c5q",
        "c5q. d5e c5q a4q", "bb4q. d5e g5q. f5e", "e5q. f5e g5q. bb4e", "a4w",
        "a5q. g5e f5q d5q", "f5h. d5q", "d5q. e5e f5q g5q", "a5h g5h",
        "c6q. bb5e a5q f5q", "d5q. e5e f5q bb5q", "a5h g5h", "f5w^"]
AH = ["F", "F", "Bb", "Bb", "F/C", "F/C", "C7", "C7", "F", "F", "Gm7", "Gm7",
      "C7", "C7", "F", "F", "Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "C7", "C7",
      "F/A", "F/A", "Bb", "Bb", "F/C", "C7", "F", "F"]
ABASS = {"F": "[f1 f2]", "Bb": "[bb0 bb1]", "F/C": "[c2 c3]", "C7": "[c2 c3]",
         "Gm7": "[g1 g2]", "Dm": "[d2 d3]", "Gm": "[g1 g2]", "F/A": "[a1 a2]"}
AR = s.section("ARIA", key="F")
AR.voice("voice").bars(join(dyn(ARIA, {0: "!mf", 8: "cresc", 11: "!f",
                                       13: "dim", 15: "!mf"})))
AR.voice("filigree", vel=30).harmony(" ".join(AH), slots="half", octave=6,
                                     pattern="1 2 3 2 1 2 3 2", unit=0.25)
AR.voice("bass").bars("!mp " + join(
    f"{ABASS[a]}h {ABASS[b]}h" for a, b in zip(AH[0::2], AH[1::2])))
AR.pedal("half")
AR.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("ARIA", 1, 63)

# ── ARIA 2: in octaves over wide arpeggios ──
A2 = s.section("ARIA2", key="F")
A2.voice("rh").bars(join(dyn(
    [voiced(m, lambda p, d, h=h: [p, p + 12]
            + ([below(p + 12, h)] if DUR[d] >= 1 else []))
     for m, h in zip(ARIA, AH[0::2])],
    {0: "!f", 8: "cresc", 12: "!ff", 13: "dim", 15: "!f"})))
A2.voice("lh", vel=50).harmony(" ".join(AH), slots="half", octave=2,
                               pattern="0 2 3 4 3 2", unit=1 / 3)
A2.pedal("half")
A2.rubato(0.05, phrase=2, shape="arch")
s.tempo_change("ARIA2", 1, 66)

# ── CADENZA ──
up = " ".join(nm(p) + "t" for p in (77, 79, 81, 82, 84, 86, 88, 89, 91, 93,
                                     94, 96, 98, 100, 101, 103))
down = " ".join(nm(p) + "t" for p in range(101, 85, -1))
CZ = s.section("CADENZA", key="F")
CZ.voice("rh").bars("!mf " + up + " cresc " + down + " | !f dn6h%^"
                    " [fn5 gn5 bn5 dn6]h&^ |")
CZ.voice("lh").bars("!mf rw | !f [gn1 gn2]w^ |")
CZ.pedal("bar")
s.tempo_change("CADENZA", 1, 72)
s.tempo_change("CADENZA", 2, 54)

# ── CORO: the chorus, twice ──
CO = ["c5e g5e e5e g5e", "c6q g5q", "b5e g5e d5e f5e", "e5q c5q",
      "a5e c6e a5e f5e", "g5e e5e c5e e5e", "d5e f5e b5e d6e", "c6q rq",
      "a5e c6e e6e c6e", "b5e g5e e5e g5e", "a5e f5e c6e a5e", "g5q e5q",
      "f5e a5e d6e c6e", "b5e d6e g6e f6e", "e6e c6e d6e b5e", "c6q rq"]
COH = ["C", "C", "G7", "C", "F", "C", "G7", "C",
       "Am", "Em", "F", "C", "Dm7", "G7", "C/G|G7", "C"]
COOM = {"C": ("c2", "g1", "e3 g3 c4"), "G7": ("g1", "d2", "f3 b3 d4"),
        "F": ("f2", "c2", "f3 a3 c4"), "Am": ("a1", "e2", "e3 a3 c4"),
        "Em": ("e2", "b1", "e3 g3 b3"), "Dm7": ("d2", "a1", "f3 a3 c4")}


def coro_bass(h, octave=False):
    if h == "C/G|G7":
        g = "[g1 g2]" if octave else "g1"
        return f"{g}e [e3 g3 c4]e' {g}e [f3 b3 d4]e'"
    b1, b2, ch = COOM[h]
    if octave:
        b1 = f"[{b1} {b1[:-1]}{int(b1[-1]) + 1}]"
        b2 = f"[{b2} {b2[:-1]}{int(b2[-1]) + 1}]"
    return f"{b1}e [{ch}]e' {b2}e [{ch}]e'"


C1 = s.section("CORO", key="C", time="2/4")
C1.voice("rh").bars(join(dyn([voiced(m, lambda p, d: [p], "'") for m in CO],
                             {0: "!mf", 8: "cresc", 12: "!f"})))
C1.voice("lh").bars("!mp " + join([coro_bass(h) for h in COH]))
s.tempo_change("CORO", 1, 116)
C2 = s.section("CORO2", key="C", time="2/4")
C2.voice("rh").bars(join(dyn(
    [voiced(m, lambda p, d, h=h: [below(p, h.split("|")[0]), p, p + 12])
     for m, h in zip(CO, COH)], {0: "!f", 8: "cresc", 12: "!ff"})))
C2.voice("lh").bars("!f " + join([coro_bass(h, octave=True) for h in COH]))
s.tempo_change("CORO2", 1, 120)

# ── DUET ──
D = s.section("DUET", key="Bb")
D.voice("soprano").bars(
    "!mf dn5q. fn5e bb5q. an5e | gn5h. dn5q | eb5q. gn5e cn6q. bb5e |"
    " an5h. rq | (rw |)*4"
    " cresc gn5q. an5e bb5q gn5q | !f eb6h. bb5q | dim cn6q. bb5e an5q gn5q |"
    " !mf fn5h. rq | fn5q. bb5e dn6q bb5q | cresc eb6h. cn6q |"
    " !f an5q. bb5e cn6q an5q | dim bb5w^ !mp |")
D.voice("baritone").bars(
    "(rw |)*4 !mf dn3q. fn3e bb3q. an3e | eb4h. cn4q |"
    " an3q. cn4e eb4q. fn4e | dn4w |"
    " cresc bb3q. cn4e dn4q bb3q | !f gn3h. gn3q | dim eb4q. dn4e cn4q bb3q |"
    " !mf an3h. rq | dn4q. fn4e fn4q dn4q | cresc gn3h. an3q |"
    " !f fn3q. gn3e an3q cn4q | dim dn4w^ !mp |")
D.voice("harp", vel=32).harmony(
    "Bb Gm Eb F7 Bb Cm7 F7 Bb Gm Eb Cm F7 Bb Eb F7 Bb", octave=1,
    pattern="0 1 2 3 2 1 2 1", unit=0.5)
D.pedal("bar")
D.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("DUET", 1, 60)
s.ritardando("DUET", 15, 17, 46)

# ── GALOP ──
GA = ["a5s a5s a5s a5s f#5e a5e", "d6s d6s d6s d6s a5e f#5e",
      "e5s e5s e5s e5s g5e e5e", "c#6s c#6s c#6s c#6s a5e e5e",
      "a5s a5s a5s a5s f#5e a5e", "b5s b5s b5s b5s g5e b5e",
      "e6s d6s c#6s b5s a5e g5e", "f#5q d5q",
      "a5e f#5e a5e d6e", "b5e g5e b5e d6e", "a5e f#5e d6e a5e",
      "g5e e5e c#6e a5e", "b5e d6e f#6e d6e", "e6e g6e e6e b5e",
      "a5e c#6e e6e g6e", "f#6q d6q"]
GH = ["D", "D", "A7", "A7", "D", "G", "A7", "D",
      "D", "G", "D/A", "A7", "Bm", "Em7", "A7", "D"]
GOOM = {"D": ("d2", "a1", "d3 f#3 a3"), "A7": ("a1", "e2", "c#3 e3 g3"),
        "G": ("g1", "d2", "b2 d3 g3"), "D/A": ("a1", "d2", "d3 f#3 a3"),
        "Bm": ("b1", "f#2", "b2 d3 f#3"), "Em7": ("e2", "b1", "d3 e3 g3")}
CIMB = {"D": ("d1 d2", "d3 f#3"), "A7": ("a0 a1", "c#3 g3"),
        "G": ("g1 g2", "b2 d3"), "D/A": ("a0 a1", "d3 f#3"),
        "Bm": ("b0 b1", "d3 f#3"), "Em7": ("e1 e2", "d3 g3")}
G1 = s.section("GALOP1", key="D", time="2/4")
G1.voice("rh").bars(join(dyn([voiced(m, lambda p, d: [p], "'") for m in GA],
                             {0: "!f", 8: "cresc", 12: "!ff"})))
G1.voice("lh").bars("!f " + join(
    f"{GOOM[h][0]}e [{GOOM[h][2]}]e' {GOOM[h][1]}e [{GOOM[h][2]}]e'"
    for h in GH))
s.tempo_change("GALOP1", 1, 152)
G2 = s.section("GALOP2", key="D", time="2/4")
G2.voice("rh").bars(join(dyn([voiced(m, lambda p, d: [p, p + 12]) for m in GA],
                             {0: "!ff", 12: "!fff"})))
G2.voice("lh").bars("!ff " + join(f"([{CIMB[h][0]}]s [{CIMB[h][1]}]s)*4"
                                  for h in GH))
s.tempo_change("GALOP2", 1, 158)

# ── STRETTA: the aria in the bass, the galop above ──
aria_d = [transpose(m.replace("^", ""), -3, key="F") for m in ARIA]
low = []
for m in aria_d:
    a, b = halves(m)
    low += [voiced(a, lambda p, d: [p - 24, p - 12]),
            voiced(b, lambda p, d: [p - 24, p - 12])]
SH = ["D", "D", "G", "G", "D/A", "D/A", "A7", "A7", "D", "D", "Em7", "Em7",
      "A7", "A7", "D", "D", "Bm", "Bm", "G", "G", "Em", "Em", "A7", "A7",
      "D/F#", "D/F#", "G", "G", "D/A", "A7", "D", "D"]
ST = s.section("STRETTA", key="D", time="2/4")
ST.voice("aria").bars(join(dyn(low, {0: "!ff", 16: "cresc", 24: "!fff"})))
ST.voice("galop", vel=62).harmony(" ".join(SH), octave=5,
                                  pattern="1 2 3 4 3 2 3 2", unit=0.25)
ST.pedal(1)
s.tempo_change("STRETTA", 1, 150)

# ── CODA ──
up = [f"[{nm(p)} {nm(p + 12)}]s" for p in range(74, 90)]
down = [f"[{nm(p - 12)} {nm(p)}]s" for p in range(50, 34, -1)]
DC = "[dn5 f#5 an5 dn6]"
AC = "[c#5 en5 gn5 an5]"
CD = s.section("CODA", key="D", time="2/4")
CD.voice("rh").bars(
    "!fff " + " ".join(up[:8]) + " | " + " ".join(up[8:]) + " |"
    f" ({DC}e> {DC}e> {AC}e> {AC}e> |)*2"
    " [dn5 f#5 an5 dn6]q> [an4 c#5 en5 gn5 an5]q> |"
    " [dn4 f#4 an4 dn5 f#5 an5 dn6]q>& rq |"
    " re [dn6 f#6 an6 dn7]e>' re [dn5 f#5 an5 dn6]e>' |"
    " [dn3 dn4 f#4 an4 dn5 f#5 an5 dn6]q>& rq |")
CD.voice("lh").bars(
    "!fff " + " ".join(down[:8]) + " | " + " ".join(down[8:])
    + " | ([dn1 dn2]e [dn1 dn2]e [an0 an1]e [an0 an1]e |)*2"
    " [dn1 dn2]q [an0 an1]q | [dn1 an1 dn2]q> rq |"
    " [dn1 dn2]e>' re [dn1 dn2]e>' re | [dn1 dn2]q> rq |")
CD.pedal(1)
s.tempo_change("CODA", 1, 164)
s.tempo_change("CODA", 5, 132)

s.arrange("INTRO ARIA ARIA2 CADENZA CORO CORO2 DUET GALOP1 GALOP2 STRETTA"
          " CODA")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "horowitz_opera_fantasy.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
