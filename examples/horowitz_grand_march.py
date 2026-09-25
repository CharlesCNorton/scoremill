#!/usr/bin/env python3
"""Grand March "Liberty Bell Park". In the manner of Horowitz.

An original march in E-flat, transcribed the way Horowitz transcribed
Sousa: a chromatic fanfare in octaves; the first strain in octaves, then
again in thicker chords; the trombone strain, its tune in the bass
octaves under after-beat chords; a trio in A-flat whose melody sits in
the middle of the keyboard, joined halfway by a piccolo obbligato
glittering above it (the three-hand effect, figured with
harmony(pattern=)); a "dogfight" break of chromatic octave runs,
interlocking chords traded between the hands, a held dominant and a
cadenza; the trio grandioso; the break again; the trio fff with a
countermelody in the bass octaves; and the stinger."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, chord_pitches

LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
ACCS = {"#": 1, "b": -1, "n": 0, "##": 2, "bb": -2}
FLATS = ["cn", "db", "dn", "eb", "en", "fn", "gb", "gn", "ab", "an", "bb", "bn"]
NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.{0,2})?([~>'_^&]*)$")


def midi(l, a, o):
    return 12 * (int(o) + 1) + LETTER[l] + ACCS.get(a or "n", 0)


def nm(m):
    return f"{FLATS[m % 12]}{m // 12 - 1}"


def voiced(frag, fn, mark=""):
    """Replace every single note with the MIDI chord fn(pitch) returns.
    Written pitches here always carry their accidental (or none, for C,
    F and G, and for naturals written plainly)."""
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        ps = sorted(set(fn(midi(*m.group(1, 2, 3)), m.group(4) or "")))
        body = nm(ps[0]) if len(ps) == 1 else "[" + " ".join(map(nm, ps)) + "]"
        out.append(body + (m.group(4) or "") + (m.group(5) or "") + mark)
    return " ".join(out)


def tone_below(m, symbol, gap=3):
    """The highest tone of `symbol` at least `gap` semitones under m."""
    pcs = {p % 12 for p in chord_pitches(symbol.split("|")[0])}
    return next(p for p in range(m - gap, m - 13, -1) if p % 12 in pcs)


def join(items):
    return " | ".join(items) + " |"


def dyn(items, marks):
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


def oompah(bass1, bass2, chord):
    return f"{bass1}e [{chord}]e' {bass2}e [{chord}]e'"


def afterbeats(chord):
    return f"re [{chord}]e' re [{chord}]e'"


def interlock(rh, lh):
    """Chords traded between the hands in sixteenths, a bar of 2/4."""
    return (f"([{rh}]s' rs)*4", f"(rs [{lh}]s')*4")


def chromatic(start, steps, direction, dur, octave_above=True):
    """A run of octaves, one semitone a step."""
    out = []
    for i in range(steps):
        p = start + direction * i
        out.append(f"[{nm(p)} {nm(p + 12)}]{dur}" if octave_above
                   else f"[{nm(p - 12)} {nm(p)}]{dur}")
    return out


s = Song(tempo=116, time="2/4", key="Eb", humanize=1, expressive=True,
         title='Grand March "Liberty Bell Park"', composer="after Horowitz")

# ── INTRO: chromatic fanfare ──
I = s.section("INTRO")
I.voice("rh").bars(
    "!ff [bb4 bb5]e' [bb4 bb5]e' [bb4 bb5]e' [bn4 bn5]e' |"
    " [c5 c6]e' [c#5 c#6]e' [dn5 dn6]e' [eb5 eb6]e' |"
    " [f5 f6]q> [bb4 bb5]q> | [bb4 dn5 f5 ab5 bb5]q> rq |")
I.voice("lh").bars(
    "!ff [bb1 bb2]e' [bb1 bb2]e' [bb1 bb2]e' [bn1 bn2]e' |"
    " [c2 c3]e' [c#2 c#3]e' [dn2 dn3]e' [eb2 eb3]e' |"
    " [f1 f2]q> [bb1 bb2]q> | [bb1 bb2]q> rq |")

# ── FIRST STRAIN ──
STRAIN = ["eb5e. f5s g5e bb5e", "eb6q bb5q", "ab5e. g5s f5e ab5e", "dn6q bb5q",
          "c6e. bb5s ab5e c6e", "bb5e. g5s eb5e g5e", "f5e. g5s an5e c6e",
          "bb5q rq", "eb5e. f5s g5e bb5e", "db6q bb5q", "c6e. bb5s ab5e c6e",
          "eb6q cb6q", "bb5e. g5s eb5e g5e", "g5e. f5s en5e g5e",
          "f5e ab5e c6e dn6e", "eb6q rq"]
S_HARM = ["Eb", "Eb", "Bb7", "Bb7", "Bb7", "Eb", "F7", "Bb7",
          "Eb", "Eb7", "Ab", "Abm", "Eb/Bb", "C7", "Fm7|Bb7", "Eb"]
OOM = {"Eb": ("eb2", "bb1", "g3 bb3 eb4"), "Bb7": ("bb1", "f2", "f3 ab3 dn4"),
       "F7": ("f2", "c2", "f3 an3 eb4"), "Eb7": ("eb2", "bb1", "g3 db4 eb4"),
       "Ab": ("ab1", "eb2", "ab3 c4 eb4"), "Abm": ("ab1", "eb2", "ab3 cb4 eb4"),
       "Eb/Bb": ("bb1", "eb2", "g3 bb3 eb4"), "C7": ("c2", "g1", "g3 bb3 en4")}


def octv(name):
    """A bass note doubled an octave below, or above where below would
    leave the keyboard."""
    p = midi(name[0], name[1:-1], name[-1])
    lo = p - 12 if p - 12 >= 21 else p
    return f"[{nm(lo)} {nm(lo + 12)}]"


def strain_bass(h, octave=False):
    if h == "Fm7|Bb7":
        b1, b2 = ("[f1 f2]", "[bb0 bb1]") if octave else ("f2", "bb1")
        return f"{b1}e [f3 ab3 eb4]e' {b2}e [f3 ab3 dn4]e'"
    b1, b2, ch = OOM[h]
    if octave:
        b1, b2 = octv(b1), octv(b2)
    return oompah(b1, b2, ch)


A1 = s.section("FIRST")
A1.voice("rh").bars(join(dyn([voiced(m, lambda p, d: [p, p + 12])
                              for m in STRAIN],
                             {0: "!mf", 8: "cresc", 11: "!f", 15: "!mf"})))
A1.voice("lh").bars("!mp " + join([strain_bass(h) for h in S_HARM]))


def thick(p, d, h):
    """A melody note with its octave above and, on longer notes, the
    chord tone under it."""
    tones = [p, p + 12]
    if d not in ("s",):
        tones.append(tone_below(p, h))
    return tones


A2 = s.section("FIRST2")
A2.voice("rh").bars(join(dyn(
    [voiced(m, lambda p, d, h=h: thick(p, d, h)) for m, h in zip(STRAIN, S_HARM)],
    {0: "!f", 8: "cresc", 11: "!ff", 15: "!f"})))
A2.voice("lh").bars("!f " + join([strain_bass(h, octave=True)
                                  for h in S_HARM]))

# ── SECOND STRAIN: the trombones ──
TROMBONE = ["c2e. dn2s eb2e g2e", "c3q g2q", "bn1e. c2s dn2e f2e", "g2q dn2q",
            "eb2e. f2s g2e c3e", "eb3q c3q", "dn2e. en2s f#2e an2e", "g2q g1q",
            "c3e. bb2s ab2e g2e", "f2q ab2q", "bb2e. ab2s g2e f2e", "eb2q bb1q",
            "ab1e. bb1s c2e eb2e", "f2e. g2s an2e c3e", "dn3q bb2q", "f2q bb1q"]
T_HARM = ["Cm", "Cm", "G7", "G7", "Cm", "Cm", "D7", "G7",
          "Cm", "Fm", "Bb7", "Eb", "Ab", "F7", "Bb7", "Bb7"]
AFTER = {"Cm": "c5 eb5 g5", "G7": "bn4 dn5 f5", "D7": "c5 f#5 an5",
         "Fm": "c5 f5 ab5", "Bb7": "dn5 f5 ab5", "Eb": "eb5 g5 bb5",
         "Ab": "eb5 ab5 c6", "F7": "eb5 f5 an5"}
B1 = s.section("SECOND")
B1.voice("trombone").bars(join(dyn([voiced(m, lambda p, d: [p, p + 12])
                                    for m in TROMBONE],
                                   {0: "!f", 8: "cresc", 12: "!ff"})))
B1.voice("rh").bars(join(dyn([afterbeats(AFTER[h]) for h in T_HARM],
                             {0: "!mp", 8: "cresc", 12: "!mf"})))
B1.variant("SECOND2", vel_scale=1.12)

# ── TRIO in A-flat: melody in the middle, piccolo above ──
TRIO = ["c5q. db5e", "eb5h", "db5q. c5e", "bb4h", "bb4q. c5e", "db5q g4q",
        "ab4h", "c5h", "eb5q. f5e", "gb5h", "f5q. eb5e", "db5h", "c5q. db5e",
        "bb4q db5q", "c5h", "ab4h",
        "f5q. gb5e", "ab5h", "eb5q. f5e", "eb5h", "dn5q. eb5e", "f5h",
        "g5q. f5e", "eb5q db5q", "c5q. db5e", "eb5q gb5q", "f5q. ab5e", "fb5h",
        "eb5q. c5e", "bb4q db5q", "ab4h", "ab4h"]
H1 = "Ab Ab Eb7 Eb7 Eb7 Eb7 Ab Ab Ab Ab7 Db Db Ab/Eb Eb7 Ab Ab"
H2 = "Db Db Ab Ab Bb7 Bb7 Eb7 Eb7 Ab Ab7 Db Dbm Ab/Eb Eb7 Ab Ab"
HARM = (H1 + " " + H2).split()
TRIO_OOM = {"Ab": ("ab1", "eb2", "ab3 c4 eb4"), "Eb7": ("eb2", "bb1", "g3 bb3 db4"),
            "Ab7": ("ab1", "eb2", "gb3 c4 eb4"), "Db": ("db2", "ab1", "f3 ab3 db4"),
            "Dbm": ("db2", "ab1", "fb3 ab3 db4"), "Ab/Eb": ("eb2", "ab1", "ab3 c4 eb4"),
            "Bb7": ("bb1", "f2", "f3 ab3 dn4")}
PICCOLO = "3 4 5 6 5 4 3 4"

T = s.section("TRIO", key="Ab")
T.voice("melody").bars(join(dyn([voiced(m, lambda p, d: [p], "_")
                                 for m in TRIO],
                                {0: "!mf", 16: "cresc", 21: "!f", 24: "dim",
                                 31: "!mf"})))
T.voice("lh").bars("!p " + join([oompah(*TRIO_OOM[h]) for h in HARM]))
picc = T.voice("piccolo", vel=34)
picc.bars("(rh |)*16")
picc.harmony(H2, octave=5, pattern=PICCOLO, unit=0.25)
T.pedal("bar")
s.tempo_change("TRIO", 1, 104)

# ── BREAK: the dogfight ──
K = s.section("BREAK")
run_up = chromatic(36, 16, 1, "s")               # C2 upward, octaves above
run_down = chromatic(80, 16, -1, "s")            # A-flat 5 downward
fm = interlock("f5 ab5 c6", "f3 ab3 c4")
db = interlock("f5 ab5 db6", "f3 ab3 db4")
bbm = interlock("f5 bb5 db6", "f3 bb3 db4")
eb7 = interlock("g5 bb5 db6", "g3 bb3 db4")
cadenza = " ".join(nm(p) + "t" for p in range(97, 81, -1))
K.voice("rh").bars(join([
    "!ff [bn4 dn5 f5 ab5]q> [bn4 dn5 f5 ab5]q>",
    "[bn4 dn5 f5 ab5]q> [c5 eb5 g5 c6]q>",
    " ".join(run_down[:8]), " ".join(run_down[8:]),
    fm[0], fm[0], db[0], db[0], "cresc " + bbm[0], eb7[0],
    "!fff [db6 eb6 g6 bb6 db7]h^&", "!f " + cadenza]))
K.voice("lh").bars(join([
    "!ff " + " ".join(run_up[:8]), " ".join(run_up[8:]),
    "[c1 c2]q> [c1 c2]q>", "[f1 f2]q> [f1 f2]q>",
    fm[1], fm[1], db[1], db[1], "cresc " + bbm[1], eb7[1],
    "!fff [eb1 eb2 bb2]h^", "rh"]))
s.tempo_change("BREAK", 1, 116)
s.tempo_change("BREAK", 12, 84)
K.variant("BREAK2", vel_scale=1.08)
s.tempo_change("BREAK2", 1, 120)
s.tempo_change("BREAK2", 12, 84)

# ── GRANDIOSO: the trio in chords, the piccolo above ──
G = s.section("GRANDIOSO", key="Ab")
G.voice("rh").bars(join(dyn(
    [voiced(m, lambda p, d, h=h: [p - 12, tone_below(p, h), p])
     for m, h in zip(TRIO, HARM)],
    {0: "!ff", 16: "cresc", 20: "!fff"})))
G.voice("lh").bars("!ff " + join([f"{octv(TRIO_OOM[h][0])}q> "
                                  f"{octv(TRIO_OOM[h][1])}q" for h in HARM]))
gp = G.voice("piccolo", vel=46)
gp.bars("(rh |)*16")
gp.harmony(H2, octave=5, pattern=PICCOLO, unit=0.25)
G.pedal("bar")
s.tempo_change("GRANDIOSO", 1, 108)

# ── GRANDIOSO 2: fff, the countermelody in the bass ──
COUNTER = ["ab1q c2q", "eb2q ab2q", "g2q f2q", "eb2q db2q", "c2q bb1q",
           "g1q bb1q", "ab1q c2q", "eb2q ab1q", "c2q eb2q", "gb2q eb2q",
           "f2q ab2q", "db3q ab2q", "eb2q f2q", "g2q eb2q", "ab2q eb2q",
           "c2q ab1q", "db2q f2q", "ab2q f2q", "eb2q c2q", "ab1q c2q",
           "dn2q f2q", "ab2q f2q", "g2q bb2q", "db3q bb2q", "ab2q c3q",
           "gb2q eb2q", "f2q db2q", "fb2q ab2q", "eb2q c2q", "bb1q db2q",
           "c2q eb2q", "ab1h"]
G2 = s.section("GRANDIOSO2", key="Ab")
G2.voice("rh").bars(join(dyn(
    [voiced(m, lambda p, d, h=h: [p, tone_below(p + 12, h), p + 12])
     for m, h in zip(TRIO, HARM)],
    {0: "!ff", 16: "cresc", 20: "!fff"})))
G2.voice("counter").bars(join(dyn([voiced(m, lambda p, d: [p, p + 12], ">")
                                   for m in COUNTER],
                                  {0: "!ff", 16: "cresc", 20: "!fff"})))
G2.pedal("bar")
s.tempo_change("GRANDIOSO2", 1, 108)
s.ritardando("GRANDIOSO2", 31, 33, 92)

# ── CODA: the stinger ──
C = s.section("CODA", key="Ab")
C.voice("rh").bars(
    "!ff [ab4 c5 eb5 ab5]q>' rq | [g4 bb4 db5 eb5 g5]q>' rq |"
    " [ab4 c5 eb5 ab5 c6]q> [ab4 c5 eb5 ab5 c6]q> |"
    " !fff [ab4 c5 eb5 ab5 c6 eb6 ab6]q>& rq | re [ab3 ab4 c5 eb5 ab5]e>' rq |")
C.voice("lh").bars(
    "!ff [ab1 ab2]q>' rq | [eb1 eb2]q>' rq | [ab1 ab2]q> [ab1 ab2]q> |"
    " !fff [ab1 eb2 ab2]q> rq | re [ab1 ab2]e>' rq |")
C.pedal(1)
s.tempo_change("CODA", 1, 112)

s.arrange("INTRO FIRST FIRST2 SECOND SECOND2 TRIO BREAK GRANDIOSO BREAK2"
          " GRANDIOSO2 CODA")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "horowitz_grand_march.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
