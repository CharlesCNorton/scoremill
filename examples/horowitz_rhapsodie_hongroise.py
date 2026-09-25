#!/usr/bin/env python3
"""Rhapsodie hongroise in A minor. In the manner of Horowitz.

After the way Horowitz played and rewrote Liszt's Hungarian Rhapsodies:
a Lento a capriccio recitative on the Hungarian minor scale with held
fermatas and a cimbalom tremolo; the lassan, a verbunkos song in dotted
rhythms with grace-note ornaments, then the same song in the cello
octaves under a pianissimo cimbalom (three hands); a cadenza of double
tremolos and a chromatic cascade; the friska in A major through four
variations (plain, in octaves over a cimbalom bass, the tune in the
deep bass under glittering figuration, and a Prestissimo of chords
traded between the hands), broken once by a soft reminiscence of the
lassan in the major; and a coda of contrary chromatic octaves and
hammered cadences."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, chord_pitches

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


def join(items):
    return " | ".join(items) + " |"


def dyn(items, marks):
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


s = Song(tempo=60, time="4/4", key="Am", humanize=1, expressive=True,
         title="Rhapsodie hongroise in A minor", composer="after Horowitz")

# ── LENTO A CAPRICCIO ──
HUNGARIAN_UP = " ".join(nm(p) + "t" for p in
                        (69, 71, 72, 75, 76, 77, 80, 81, 83, 84, 87, 88, 89,
                         92, 93, 95))
L = s.section("LENTO")
L.voice("rh").bars(
    "!f [a4 a5]q.> [g#4 g#5]e [f4 f5]e. [e4 e5]s [d#4 d#5]q^ |"
    " [e4 e5]h.^ rq |"
    " !mf " + HUNGARIAN_UP + " !f [a5 c6 e6 a6]h&^ |"
    " !p (e5t f5t)*8 cresc (e5t f5t)*8 |"
    " !f [e5 g#5 b5 e6]h.&^ rq |")
L.voice("lh").bars(
    "!f [a1 a2]w | [e1 e2]h.^ rq | rh [a1 e2 a2]h^ | !p [e1 e2]w |"
    " !f [e1 e2 b2]h.^ rq |")
L.pedal("bar")
s.tempo_change("LENTO", 1, 52)

# ── LASSAN ──
V = ["+b4 a4q. c5e e5q. d#5e", "e5e. f5s e5e. d5s c5q b4q",
     "c5q. b4e a4q. g#4e", "a4e. b4s c5e. d5s f5h",
     "+f5 e5q. f5e g#5q. a5e", "b5e. a5s g#5e. f5s e5h",
     "a4e c5e e5e a5e a5q. g#5e", "a5q rq rh",
     "+d6 c6q. a5e f5q. e5e", "g5e. f5s e5e. d5s c5h",
     "d5q. e5e f5q. g#5e", "a5e. g#5s f5e. e5s d5h",
     "c5e. d#5s e5e. f5s g#5q a5q", "d6q. c6e a5q. f5e",
     "e5e. f5s g#5e. b5s d6q c6e b5e", "a5h. rq"]
VH = ["Am", "E7", "Am", "Dm", "Am/E", "E7", "Am", "Am",
      "F", "C/E", "Dm", "E7", "Am", "Dm/F", "E7", "Am"]
BASS = {"Am": ("[a0 a1]", "e2 a2 c3"), "E7": ("[e1 e2]", "e2 g#2 d3"),
        "Dm": ("[d1 d2]", "d2 f2 a2"), "Am/E": ("[e1 e2]", "e2 a2 c3"),
        "F": ("[f1 f2]", "f2 a2 c3"), "C/E": ("[e1 e2]", "e2 g2 c3"),
        "Dm/F": ("[f1 f2]", "f2 a2 d3")}


def verbunkos(h):
    b, ch = BASS[h]
    return f"{b}q. [{ch}]e [{ch}]q [{ch}]q"


def filled(frag, h):
    return voiced(frag, lambda p, d: [p - 12, p]
                  + ([below(p, h)] if DUR.get(d, 0) >= 1 else []))


LA = s.section("LASSAN")
LA.voice("rh").bars(join(dyn([filled(v, h) for v, h in zip(V, VH)],
                             {0: "!mf", 4: "cresc", 5: "!f", 6: "dim",
                              7: "!mp", 8: "!mf", 10: "cresc", 12: "!ff",
                              14: "dim", 15: "!mf"})))
LA.voice("lh").bars("!mp " + join([verbunkos(h) for h in VH]))
LA.pedal("half")
LA.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("LASSAN", 1, 66)
s.ritardando("LASSAN", 15, 17, 54)

# ── LASSAN 2: the cello octaves under the cimbalom ──
CIMB = {"Am": ("c6", "e6"), "E7": ("b5", "d6"), "Dm": ("a5", "d6"),
        "Am/E": ("c6", "e6"), "F": ("a5", "c6"), "C/E": ("g5", "c6"),
        "Dm/F": ("a5", "d6")}
L2 = s.section("LASSAN2")
L2.voice("cimbalom").bars(join(dyn(
    [f"({CIMB[h][0]}t {CIMB[h][1]}t)*16" for h in VH],
    {0: "!pp", 8: "cresc", 12: "!p", 14: "dim", 15: "!pp"})))
L2.voice("tenor").bars(join(dyn(
    [voiced(re.sub(r"\+\S+ ", "", v), lambda p, d: [p - 24, p - 12])
     for v in V], {0: "!f", 6: "dim", 7: "!mf", 8: "cresc", 12: "!ff",
                   14: "dim", 15: "!mf"})))
L2.voice("bass").bars("!p " + join([BASS[h][0] + "w" for h in VH]))
L2.pedal("half")
L2.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("LASSAN2", 1, 64)
s.ritardando("LASSAN2", 15, 17, 50)

# ── CADENZA ──
cascade = " ".join(f"[{nm(p - 12)} {nm(p)}]t" for p in range(88, 56, -1))
CZ = s.section("CADENZA")
CZ.voice("rh").bars("!p (e5t g#5t)*8 cresc (e5t g#5t)*8 | !ff " + cascade
                    + " |")
CZ.voice("lh").bars("!p (e2t b2t)*8 cresc (e2t b2t)*8 | !ff [e1 e2]w |")
CZ.pedal("bar")
s.tempo_change("CADENZA", 1, 72)
s.tempo_change("CADENZA", 2, 96)

# ── FRISKA: the tune ──
F = ["e5s e5s a5e c#6e a5e", "e5s e5s a5e c#6e e6e", "d6s c#6s b5e g#5e e5e",
     "c#6e a5e a5q", "e5s e5s a5e c#6e a5e", "d5s f#5s a5e d6e f#6e",
     "e6s d6s c#6e b5e g#5e", "a5q rq",
     "f#5s f#5s a5e c#6e f#6e", "e6s d#6s c#6e b5e g#5e",
     "a5s a5s d6e f#6e d6e", "c#6s c#6s e6e a6e e6e",
     "d6s c#6s b5e d6e f#6e", "e6s d6s b5e g#5e e5e", "a5e c#6e e6e a6e",
     "a6q rq"]
FH = ["A", "A", "E7", "A", "A", "D", "E7", "A",
      "F#m", "C#m", "D", "A/E", "Bm", "E7", "A", "A"]
OOM = {"A": ("a1", "e2", "c#3 e3 a3"), "E7": ("e2", "b1", "d3 e3 g#3"),
       "D": ("d2", "a1", "d3 f#3 a3"), "F#m": ("f#2", "c#2", "c#3 f#3 a3"),
       "C#m": ("c#2", "g#1", "c#3 e3 g#3"), "A/E": ("e2", "a1", "c#3 e3 a3"),
       "Bm": ("b1", "f#2", "b2 d3 f#3")}
CIMB_BASS = {"A": ("a1 a2", "c#3 e3"), "E7": ("e1 e2", "d3 g#3"),
             "D": ("d1 d2", "d3 f#3"), "F#m": ("f#1 f#2", "c#3 f#3"),
             "C#m": ("c#1 c#2", "c#3 e3"), "A/E": ("e1 e2", "c#3 a3"),
             "Bm": ("b0 b1", "d3 f#3")}

F1 = s.section("FRISKA1", key="A", time="2/4")
F1.voice("rh").bars(join(dyn([voiced(f, lambda p, d: [p], "'") for f in F],
                             {0: "!mf", 8: "cresc", 11: "!f", 15: "!mf"})))
F1.voice("lh").bars("!mp " + join(
    [f"{OOM[h][0]}e [{OOM[h][2]}]e' {OOM[h][1]}e [{OOM[h][2]}]e'"
     for h in FH]))
s.tempo_change("FRISKA1", 1, 132)

F2 = s.section("FRISKA2", key="A", time="2/4")
F2.voice("rh").bars(join(dyn([voiced(f, lambda p, d: [p, p + 12]) for f in F],
                             {0: "!f", 8: "cresc", 11: "!ff", 15: "!f"})))
F2.voice("lh").bars("!f " + join(
    [f"([{CIMB_BASS[h][0]}]s [{CIMB_BASS[h][1]}]s)*4" for h in FH]))
s.tempo_change("FRISKA2", 1, 144)

# ── REMINISCENCE: the lassan remembered, in the major ──
RM = s.section("REMINISCENCE", key="A")
RM.voice("song").bars(
    "!pp a5q. c#6e e6q. d#6e | e6e. f#6s e6e. dn6s c#6q b5q |"
    " c#6q. b5e a5q. g#5e | a5e. b5s c#6e. dn6s f#6h |"
    " e6q. f#6e g#6q. a6e | b6e. a6s g#6e. f#6s e6h |"
    " a5e c#6e e6e a6e a6q. g#6e | a6w^ |")
harp = RM.voice("harp", vel=26)
harp.harmony("A E7 A D A/E E7 A A", octave=2, pattern="0 2 3 4 5 4 3 2",
             unit=0.5)
RM.pedal("bar")
RM.soft()
RM.rubato(0.06, phrase=2, shape="cradle")
s.tempo_change("REMINISCENCE", 1, 58)
s.ritardando("REMINISCENCE", 7, 9, 42)

# ── FRISKA 3: the tune in the deep bass, figuration above ──
F3 = s.section("FRISKA3", key="A", time="2/4")
F3.voice("bass").bars(join(dyn([voiced(f, lambda p, d: [p - 36, p - 24])
                                for f in F],
                               {0: "!ff", 15: "!ff"})))
sparkle = F3.voice("sparkle", vel=58)
sparkle.harmony(" ".join(FH), octave=5, pattern="1 2 3 4 5 4 3 2",
                unit=0.25)
s.tempo_change("FRISKA3", 1, 152)

# ── FRISKA 4: Prestissimo, chords traded between the hands ──
F4 = s.section("FRISKA4", key="A", time="2/4")
F4.voice("rh").bars(join(dyn(
    [voiced(f, lambda p, d, h=h: [below(p, h), p, p + 12] if p + 12 <= 108
            else [below(p, h), p])
     for f, h in zip(F, FH)], {0: "!ff", 8: "cresc", 11: "!fff"})))
F4.voice("lh").bars("!ff " + join(
    [f"(rs [{CIMB_BASS[h][0]}]s)*4" for h in FH]))
s.tempo_change("FRISKA4", 1, 168)

# ── CODA ──
up = [f"[{nm(p)} {nm(p + 12)}]s" for p in range(76, 92)]
down = [f"[{nm(p - 12)} {nm(p)}]s" for p in range(52, 36, -1)]
C = s.section("CODA", key="A", time="2/4")
C.voice("rh").bars(
    "!fff " + " ".join(up[:8]) + " | " + " ".join(up[8:]) + " |"
    " ([a4 c#5 e5 a5]e> [a4 c#5 e5 a5]e> [e4 g#4 b4 e5]e> [e4 g#4 b4 e5]e> |)*2"
    " [a4 c#5 e5 a5 c#6]q> [e4 g#4 b4 dn5 e5]q> |"
    " [a4 c#5 e5 a5 c#6 e6 a6]q>& rq | re [a5 c#6 e6 a6]e>' rq |"
    " [a3 e4 a4 c#5 e5 a5]q>& rq |")
C.voice("lh").bars(
    "!fff " + " ".join(down[:8]) + " | " + " ".join(down[8:]) + " |"
    " ([a1 a2]e [a1 a2]e [e1 e2]e [e1 e2]e |)*2 [a1 a2]q [e1 e2]q |"
    " [a0 a1 e2 a2]q> rq | [a1 a2]e>' re rq | [a0 a1]q> rq |")
C.pedal(1)
s.tempo_change("CODA", 1, 176)
s.tempo_change("CODA", 3, 150)

s.arrange("LENTO LASSAN LASSAN2 CADENZA FRISKA1 FRISKA2 REMINISCENCE"
          " FRISKA3 FRISKA4 CODA")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "horowitz_rhapsodie_hongroise.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
