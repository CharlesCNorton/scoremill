#!/usr/bin/env python3
"""Elegie in B-flat minor. In the manner of Rachmaninoff.

A long-breathed melody over the chromatic "line cliche" bass
(B-flat, A, A-flat, G) and rolling triplet arpeggios, colored by the
Neapolitan and half-diminished chords; a passionate middle section in
D-flat with the melody in octaves over sweeping sixteenths, rising to an
fff climax that falls through the Neapolitan to the dominant; the
return with the melody in the cello register under syncopated chords,
then in full chords over sixteenths; a coda of echoes over a B-flat
pedal under the soft pedal."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.?)?([~>'_^&]*)$")


def shifted(frag, octaves_down=0, double=None):
    """Move single notes down whole octaves; with `double` given as
    +1 or -1, add the octave above or below."""
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        l, a, o, d, marks = m.groups()
        a, o = a or "", int(o) - octaves_down
        if double is None:
            out.append(f"{l}{a}{o}{d or ''}{marks}")
        else:
            lo, hi = sorted((o, o + double))
            out.append(f"[{l}{a}{lo} {l}{a}{hi}]{d or ''}{marks}")
    return " ".join(out)


def flow(t):
    """Two beats of triplet eighths over four tones, low to high."""
    return f"{{{t[0]} {t[1]} {t[2]}}}q {{{t[3]} {t[2]} {t[1]}}}q"


def sweep(t):
    """Two beats of sixteenths over five tones: up and back."""
    return " ".join(p + "s" for p in (t[0], t[1], t[2], t[3], t[4],
                                      t[3], t[2], t[1]))


def bars(halves, fn):
    """Join half-bar figures into bars."""
    pairs = [fn(halves[i]) + " " + fn(halves[i + 1])
             for i in range(0, len(halves), 2)]
    return " | ".join(pairs) + " |"


T = {  # four-tone triplet shapes
    "Bbm": ["bb1", "f2", "db3", "f3"], "Bbm/A": ["an1", "f2", "db3", "f3"],
    "Bbm7/Ab": ["ab1", "f2", "db3", "f3"],
    "Eb7/G": ["gn1", "eb2", "bb2", "db3"],
    "Gbmaj7": ["gb1", "db2", "bb2", "f3"], "Cb/Eb": ["eb2", "gb2", "cb3", "eb3"],
    "F7": ["f1", "c2", "an2", "eb3"], "F7b9": ["f1", "an2", "eb3", "gb3"],
    "Ebm/Gb": ["gb1", "eb2", "bb2", "gb3"], "Co7/Gb": ["gb1", "c2", "eb2", "bb2"],
    "F": ["f1", "c2", "an2", "c3"], "Db": ["db2", "ab2", "f3", "ab3"],
    "Db/C": ["c2", "ab2", "f3", "ab3"], "Bbm7": ["bb1", "f2", "db3", "ab3"],
    "Eb9": ["eb2", "bb2", "db3", "gn3"], "Gb": ["gb1", "db2", "bb2", "db3"],
    "Gb/F": ["f1", "db2", "bb2", "db3"], "Ebm7": ["eb2", "bb2", "gb3", "bb3"],
    "Ab7": ["ab1", "eb2", "c3", "gb3"], "Db/F": ["f1", "db2", "ab2", "f3"],
    "Cb": ["cb2", "gb2", "eb3", "gb3"], "Bbm/F": ["f1", "db2", "bb2", "f3"],
    "Ebm/Bb": ["bb1", "gb2", "eb3", "gb3"], "Gb/Bb": ["bb1", "gb2", "db3", "gb3"],
}
S = {  # five-tone sixteenth shapes
    "Db": ["db2", "ab2", "db3", "f3", "ab3"], "Bbm": ["bb1", "f2", "bb2", "db3", "f3"],
    "Gb": ["gb1", "db2", "gb2", "bb2", "db3"], "Ab7": ["ab1", "eb2", "gb2", "c3", "eb3"],
    "Db/F": ["f1", "db2", "ab2", "db3", "f3"], "Ebm7": ["eb2", "bb2", "db3", "gb3", "bb3"],
    "Fm": ["f1", "c2", "f2", "ab2", "c3"], "Eb7": ["eb2", "bb2", "db3", "gn3", "bb3"],
    "Db7": ["db2", "ab2", "cb3", "f3", "ab3"], "Gbm": ["gb1", "db2", "gb2", "bbb2", "db3"],
    "Db/Ab": ["ab1", "f2", "ab2", "db3", "f3"], "Gb/Bb": ["bb1", "gb2", "bb2", "db3", "gb3"],
    "Cb": ["cb2", "gb2", "cb3", "eb3", "gb3"], "F7": ["f1", "c2", "eb2", "an2", "c3"],
    "Ebm": ["eb2", "bb2", "eb3", "gb3", "bb3"], "F7b9": ["f1", "c2", "eb2", "gb2", "an2"],
    "Db/C": ["c2", "ab2", "db3", "f3", "ab3"], "Bbm7": ["bb1", "f2", "bb2", "db3", "ab3"],
    "Eb9": ["eb2", "bb2", "db3", "f3", "gn3"], "Gb/F": ["f1", "db2", "gb2", "bb2", "db3"],
    "Bbm/F": ["f1", "db2", "f2", "bb2", "db3"],
}

A_HARM = ["Bbm", "Bbm/A", "Bbm7/Ab", "Eb7/G", "Gbmaj7", "Cb/Eb", "F7", "F7b9",
          "Bbm", "Bbm/A", "Bbm7/Ab", "Eb7/G", "Ebm/Gb", "Co7/Gb", "F", "F7",
          "Db", "Db/C", "Bbm7", "Eb9", "Gb", "Gb/F", "Ebm7", "Ab7",
          "Db", "Db/F", "Gb", "Cb", "Bbm/F", "F7", "Bbm", "Bbm"]
A_MEL = ["f4q db5h c5e bb4e", "ab4q. bb4e c5q db5q", "f5h eb5h",
         "db5q c5q an4h", "f4q db5h c5e bb4e", "ab4q. bb4e c5q eb5q",
         "gb5h f5q eb5q", "db5q c5q c5h",
         "f5q ab5h gb5e f5e", "f5q. db5e eb5q f5q", "gb5q bb5h ab5e gb5e",
         "gb5q. eb5e f5q gb5q", "db6h. c6q", "bb5h. ab5q",
         "gb5q f5q eb5q c5q", "db5w"]

s = Song(tempo=60, time="4/4", key="Bbm", humanize=1, expressive=True)

# ── INTRO: the accompaniment alone ──
intro = s.section("INTRO")
intro.voice("rh").bars("rw | rw |")
intro.voice("lh").bars("!pp " + bars(["Bbm"] * 4, lambda h: flow(T[h])))
intro.pedal("half")

# ── A ──
A = s.section("A")
mel = list(A_MEL)
mel[0] = "!p " + mel[0]
mel[8] = "cresc " + mel[8]
mel[10] = "!mf " + mel[10]
mel[11] = "cresc " + mel[11]
mel[12] = "!f " + mel[12]
mel[13] = "dim " + mel[13]
mel[15] = "!p " + mel[15]
A.voice("rh").bars(" | ".join(mel) + " |")
lh = bars(A_HARM, lambda h: flow(T[h])).split(" | ")
lh[0] = "!pp " + lh[0]
lh[8] = "cresc " + lh[8]
lh[12] = "!mp " + lh[12]
lh[13] = "dim " + lh[13]
lh[15] = "!pp " + lh[15]
A.voice("lh").bars(" | ".join(lh))
A.pedal("half")
A.rubato(0.05, phrase=2, shape="arch")

# ── B: D-flat, piu mosso ──
B = s.section("B", key="Db")
B.voice("rh").bars(" | ".join([
    "!mf " + shifted("ab4q. db5e f5h", double=1),
    shifted("f5q. eb5e db5q c5q", double=1),
    shifted("db5q bb4q eb5q. c5e", double=1),
    shifted("db5w", double=1),
    "cresc " + shifted("f5q. gb5e ab5q bb5q", double=1),
    shifted("gb5q. f5e eb5q c5q", double=1),
    "!f " + shifted("ab5q. gn5e f5q db5q", double=1),
    shifted("eb5q. f5e gb5q ab5q", double=1),
    "!ff [ab5 db6 f6 ab6]h. [cb6 f6 ab6 cb7]q",
    "[bb5 db6 gb6 bb6]q. [ab5 ab6]e [gb5 bb5 db6 gb6]q [bbb5 db6 gb6 bbb6]q",
    "cresc [ab5 db6 f6 ab6]q. [bb5 bb6]e [c6 eb6 gb6 c7]q [db6 gb6 ab6 db7]q",
    "!fff [eb6 gb6 bb6 eb7]h.> [db6 gb6 bb6 db7]q",
    "[cb6 eb6 gb6 cb7]h> [an5 c6 eb6 an6]h>",
    "dim " + shifted("bb5q. c6e db6q bb5q", double=1),
    shifted("gb5q. f5e eb5q c5q", double=1),
    "!p " + shifted("db5h c5h", double=1),
]) + " |")
B_HARM = ["Db", "Db", "Bbm", "Bbm", "Gb", "Ab7", "Db", "Db",
          "Db/F", "Gb", "Ebm7", "Ab7", "Fm", "Bbm", "Eb7", "Ab7",
          "Db", "Db7", "Gb", "Gbm", "Db/Ab", "Ab7", "Gb", "Gb/Bb",
          "Cb", "F7", "Bbm", "Gb", "Ebm", "F7", "F7", "F7b9"]
lh = bars(B_HARM, lambda h: sweep(S[h])).split(" | ")
lh[0] = "!mp " + lh[0]
lh[4] = "cresc " + lh[4]
lh[6] = "!f " + lh[6]
lh[8] = "!ff " + lh[8]
lh[11] = "!fff " + lh[11]
lh[13] = "dim " + lh[13]
lh[15] = "!p " + lh[15]
B.voice("lh").bars(" | ".join(lh))
B.pedal("half")
B.rubato(0.05, phrase=2, shape="arch")
s.tempo_change("B", 1, 72)
s.ritardando("B", 1, 9, 80)
s.tempo_change("B", 12, 64)
s.ritardando("B", 14, 17, 50)

# ── RETURN 1: the melody in the cello register, syncopated chords above ──
R1 = s.section("RET1")
tenor = [shifted(m, octaves_down=1, double=-1) for m in A_MEL[:8]]
tenor[0] = "!mf " + tenor[0]
tenor[4] = "cresc " + tenor[4]
tenor[6] = "!f " + tenor[6]
tenor[7] = "dim " + tenor[7]
R1.voice("tenor").bars(" | ".join(tenor) + " !mp |")
SYNC = {"Bbm": "bb4 db5 f5", "Bbm/A": "bb4 db5 f5", "Bbm7/Ab": "bb4 db5 f5",
        "Eb7/G": "bb4 db5 eb5", "Gbmaj7": "bb4 db5 f5", "Cb/Eb": "cb5 eb5 gb5",
        "F7": "an4 c5 eb5", "F7b9": "an4 eb5 gb5", "Ebm/Gb": "bb4 eb5 gb5",
        "Co7/Gb": "bb4 c5 eb5", "F": "an4 c5 f5"}
R1.voice("rh").bars("!p " + bars(A_HARM[:16],
                                 lambda h: f"re [{SYNC[h]}]e re [{SYNC[h]}]e"))
BASS = {"Bbm": "bb1", "Bbm/A": "an1", "Bbm7/Ab": "ab1", "Eb7/G": "gn1",
        "Gbmaj7": "gb1", "Cb/Eb": "eb2", "F7": "f1", "F7b9": "f1",
        "Ebm/Gb": "gb1", "Co7/Gb": "gb1", "F": "f1"}
R1.voice("bass").bars("!mp " + bars(A_HARM[:16], lambda h: BASS[h] + "h"))
R1.pedal("half")
R1.rubato(0.04, phrase=2, shape="cradle")

# ── RETURN 2: full chords over sixteenths ──
R2 = s.section("RET2")
R2.voice("rh").bars(" | ".join([
    "!mf " + shifted(A_MEL[8], octaves_down=-1, double=-1),
    shifted(A_MEL[9], octaves_down=-1, double=-1),
    "cresc " + shifted(A_MEL[10], octaves_down=-1, double=-1),
    shifted(A_MEL[11], octaves_down=-1, double=-1),
    "!ff [db6 f6 ab6 db7]h.> [c6 f6 ab6 c7]q",
    "[bb5 db6 gb6 bb6]h. [ab5 cb6 eb6 ab6]q",
    "dim [gb5 bb5 db6 gb6]q [f5 bb5 db6 f6]q [eb5 an5 c6 eb6]q [c5 f5 an5 c6]q",
    "!p [db5 f5 bb5 db6]w",
]) + " |")
lh = bars(A_HARM[16:], lambda h: sweep(S[h])).split(" | ")
lh[0] = "!mp " + lh[0]
lh[2] = "cresc " + lh[2]
lh[4] = "!f " + lh[4]
lh[6] = "dim " + lh[6]
lh[7] = "!pp " + lh[7]
R2.voice("lh").bars(" | ".join(lh))
R2.pedal("half")
R2.rubato(0.05, phrase=2, shape="arch")

# ── CODA: echoes over a B-flat pedal ──
C = s.section("CODA")
C.voice("rh").bars(
    "!pp f5q db6h c6e bb5e | gb5h. f5q | f4q db5h c5e bb4e | gb4h. f4q |"
    " !ppp [db5 f5]h [eb5 gb5]h | [db5 f5]w | [bb4 db5 f5 bb5]w& |"
    " [f5 bb5 db6 f6]w& |")
C_HARM = ["Bbm", "Bbm", "Ebm/Bb", "Ebm/Bb", "Bbm", "Bbm", "Gb/Bb", "Gb/Bb",
          "Bbm", "Ebm/Bb", "Bbm", "Bbm"]
C.voice("lh").bars("!pp " + bars(C_HARM, lambda h: flow(T[h]))
                   + " [bb1 f2 db3]w& | [bb0 bb1]w |")
C.pedal("half")
C.soft()
s.tempo_change("CODA", 1, 54)
s.ritardando("CODA", 5, 9, 34)

s.arrange("INTRO A B RET1 RET2 CODA")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "rachmaninoff_elegie.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
