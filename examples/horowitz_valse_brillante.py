#!/usr/bin/env python3
"""Valse brillante in F minor. In the manner of Horowitz.

A chromatic introduction in sixths with a flourish; a bittersweet waltz
theme; the theme again in octaves, laced with runs; a scherzando episode
in A-flat on rapid repeated notes; a trio in D-flat with the melody in
the tenor, filigree above and bass below (the three-hand effect); a
chromatic cadenza; the theme in full chords; an accelerating coda of
chromatic octaves and hammered cadences."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.?)?([~>'_^&]*)$")


def octaves(frag):
    """Double every single note of a fragment an octave above."""
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        l, a, o, d, marks = m.groups()
        a = a or ""
        out.append(f"[{l}{a}{o} {l}{a}{int(o) + 1}]{d or ''}{marks}")
    return " ".join(out)


def waltz(bass, chord, stacc=True, bass_stacc=False):
    mark = "'" if stacc else ""
    bmark = "'" if bass_stacc else ""
    return f"{bass}q{bmark} [{chord}]q{mark} [{chord}]q{mark}"


def ripple(t):
    """Twelve sixteenths rippling over four chord tones, low to high."""
    seq = [t[0], t[1], t[2], t[3], t[2], t[1]] * 2
    return " ".join(p + "s" for p in seq)


def bars(items):
    return " | ".join(items) + " |"


s = Song(tempo=176, time="3/4", key="Fm", humanize=1, expressive=True)

# ── INTRO ──
intro = s.section("INTRO")
intro.voice("rh").bars(
    "!p [en5 c6]q [eb5 cb6]q [dn5 bb5]q |"
    " [db5 an5]q [c5 ab5]q [bn4 g5]q |"
    " cresc c4s en4s g4s bb4s c5s en5s g5s bb5s c6s en6s g6s bb6s |"
    " !f [bb5 c6 en6 g6 c7]h.& |"
    " !mp {c7 bn6 bb6 an6 ab6 g6}q {gb6 f6 en6 eb6 dn6 db6}q"
    " {c6 bn5 bb5 an5 ab5 g5}q |")
intro.voice("lh").bars(
    "!p [c2 c3]h. | [c2 c3]h. | cresc [c2 c3]h. |"
    " !f [c1 c2 g2 bb2 en3]h.& | !mp [c2 c3]q rh |")
intro.pedal("bar")
s.tempo_change("INTRO", 1, 120)
s.tempo_change("INTRO", 4, 58)
s.tempo_change("INTRO", 5, 132)

# ── THEME ──
MELODY = [
    "c5q. db5e c5q", "g5h f5q", "en5q f5q g5q", "ab5h g5q",
    "bb5q. ab5e g5q", "f5h en5q", "f5q ab5q c6q", "f5h.",
    "eb5q. f5e eb5q", "bb5h ab5q", "g5q ab5q bb5q", "c6h bb5q",
    "db6q. c6e bb5q", "ab5q g5q f5q", "en5q f5q g5q", "f5h.",
]
HARM = [  # (bass, variation bass octave, chord)
    ("f2", "[f1 f2]", "f3 ab3 c4"), ("c2", "[c2 c3]", "f3 ab3 c4"),
    ("c2", "[c2 c3]", "en3 g3 bb3"), ("en2", "[en1 en2]", "g3 bb3 c4"),
    ("g1", "[g1 g2]", "en3 g3 bb3"), ("c2", "[c2 c3]", "en3 g3 bb3"),
    ("f2", "[f1 f2]", "f3 ab3 c4"), ("c2", "[c2 c3]", "f3 ab3 c4"),
    ("eb2", "[eb1 eb2]", "g3 bb3 db4"), ("bb1", "[bb1 bb2]", "g3 bb3 db4"),
    ("ab1", "[ab1 ab2]", "ab3 c4 eb4"), ("eb2", "[eb1 eb2]", "ab3 c4 eb4"),
    ("bb1", "[bb1 bb2]", "f3 bb3 db4"), ("c2", "[c2 c3]", "f3 ab3 c4"),
    ("c2", "[c2 c3]", "en3 g3 bb3"), ("f2", "[f1 f2]", "f3 ab3 c4"),
]
theme = s.section("THEME")
mel = list(MELODY)
mel[0] = "!mp " + mel[0]
mel[8] = "cresc " + mel[8]
mel[11] = "!mf " + mel[11]
mel[12] = "dim " + mel[12]
mel[15] = "!mp " + mel[15]
theme.voice("rh").bars(bars(mel))
theme.voice("lh").bars("!p " + bars([waltz(b, c) for b, _o, c in HARM]))
theme.pedal("bar")
theme.rubato(0.06, phrase=4, shape="arch")

# ── VARIATION: octaves and runs ──
var = s.section("VARIATION")
v = [octaves(m) for m in MELODY]
v[0] = "!mf " + v[0]
v[1] = "+ab6 " + v[1]
v[7] = "[f5 f6]q {c6 bb5 ab5 g5 f5 en5}q {db6 c6 bb5 ab5 g5 f5}q"
v[8] = "cresc " + v[8]
v[9] = "+c7 " + v[9]
v[11] = "!f [c6 c7]h {bb5 c6 db6 eb6 f6 g6}q"
v[12] = "dim " + v[12]
v[15] = "!mf [f5 f6]h {c6 ab5 f5 c5 ab4 f4}q"
var.voice("rh").bars(bars(v))
var.voice("lh").bars("!mp " + bars([waltz(o, c) for _b, o, c in HARM]))
var.pedal("bar")
var.rubato(0.04, phrase=4, shape="arch")

# ── EPISODE: scherzando in A-flat, repeated notes ──
ep = s.section("EPISODE", key="Ab")
ep.voice("rh").bars(
    "!mp c6s' c6s' c6s' c6s' eb6e' c6e' ab5q' |"
    " bb5s' bb5s' bb5s' bb5s' db6e' bb5e' g5q' |"
    " ab5s' g5s' ab5s' bb5s' c6e' db6e' eb6q' |"
    " ab6q' rh |"
    " eb6s' eb6s' eb6s' eb6s' f6e' eb6e' c6q' |"
    " db6s' db6s' db6s' db6s' f6e' db6e' ab5q' |"
    " g5e' bb5e' db6e' eb6e' g6e' bb6e' |"
    " ab6q' rh |"
    " !mf c6s' c6s' c6s' c6s' ab5e' f5e' c5q' |"
    " bb5s' bb5s' bb5s' bb5s' g5e' en5e' c5q' |"
    " ab5s' ab5s' ab5s' ab5s' c6e' ab5e' f5q' |"
    " f5s' f5s' f5s' f5s' ab5e' db6e' f6q' |"
    " cresc f6e' db6e' bb5e' f5e' db5e' bb4e' |"
    " c5e' en5e' g5e' bb5e' c6e' en6e' |"
    " !f f6q' c6q' ab5q' |"
    " !mf g5q' bb5q' c6q' |")
EP = [("ab2", "c4 eb4"), ("eb2", "g3 db4"), ("bb1", "g3 db4"),
      ("ab2", "c4 eb4"), ("ab2", "c4 eb4"), ("db2", "f3 ab3"),
      ("eb2", "g3 db4"), ("ab1", "c4 eb4"), ("f2", "ab3 c4"),
      ("c2", "en3 bb3"), ("f2", "ab3 c4"), ("db2", "f3 ab3"),
      ("bb1", "f3 db4"), ("c2", "en3 bb3"), ("f2", "ab3 c4"),
      ("c2", "en3 bb3")]
ep.voice("lh").bars("!p " + bars([waltz(b, c, bass_stacc=True)
                                   for b, c in EP]))
ep.rubato(0.02, phrase=4, shape="arch")

# ── TRIO in D-flat: tenor melody, filigree above, bass below ──
trio = s.section("TRIO", key="Db")
TENOR = ["f3q ab3q db4q", "f4h eb4q", "db4q. c4e bb3q", "ab3h.",
         "bb3q db4q f4q", "gn4h f4q", "eb4q. db4e c4q", "eb4h.",
         "f3q ab3q db4q", "cb4h bb3q", "bb3q db4q gb4q", "db4h bbb3q",
         "ab3q. db4e f4q", "eb4q gb4q c4q", "db4h.", "rh."]
TENOR[4] = "cresc " + TENOR[4]
TENOR[5] = "!f " + TENOR[5]
TENOR[6] = "dim " + TENOR[6]
TENOR[8] = "!mf " + TENOR[8]
TRIO_H = [  # (bass, filigree tones)
    ("[db1 db2]", ["db5", "f5", "ab5", "db6"]),
    ("[db1 db2]", ["db5", "f5", "ab5", "db6"]),
    ("[gb1 gb2]", ["db5", "gb5", "bb5", "db6"]),
    ("[db1 db2]", ["db5", "f5", "ab5", "db6"]),
    ("[bb1 bb2]", ["db5", "f5", "bb5", "db6"]),
    ("[eb1 eb2]", ["db5", "gn5", "bb5", "eb6"]),
    ("[ab1 ab2]", ["eb5", "gb5", "ab5", "c6"]),
    ("[ab1 ab2]", ["eb5", "gb5", "ab5", "c6"]),
    ("[db1 db2]", ["db5", "f5", "ab5", "db6"]),
    ("[db1 db2]", ["db5", "f5", "ab5", "cb6"]),
    ("[gb1 gb2]", ["db5", "gb5", "bb5", "db6"]),
    ("[gb1 gb2]", ["db5", "gb5", "bbb5", "db6"]),
    ("[ab1 ab2]", ["db5", "f5", "ab5", "db6"]),
    ("[ab1 ab2]", ["eb5", "gb5", "ab5", "c6"]),
    ("[db1 db2]", ["db5", "f5", "ab5", "db6"]),
    ("[db1 db2]", ["db5", "f5", "ab5", "db6"]),
]
trio.voice("fil").bars("!pp " + bars([ripple(t) for _b, t in TRIO_H]))
trio.voice("tenor").bars("!mf " + bars(TENOR))
trio.voice("bass").bars("!p " + bars([f"{b}h." for b, _t in TRIO_H]))
trio.pedal("bar")
trio.rubato(0.05, phrase=4, shape="cradle")
s.tempo_change("TRIO", 1, 138)
s.ritardando("TRIO", 15, 17, 112)

# ── CADENZA ──
cad = s.section("CADENZA")
cad.voice("rh").bars(
    "!f {c7 bn6 bb6 an6 ab6 gn6}q {gb6 f6 en6 eb6 dn6 db6}q"
    " {c6 bn5 bb5 an5 ab5 gn5}q |"
    " dim {gb5 f5 en5 eb5 dn5 db5}q {c5 bn4 bb4 an4 ab4 gn4}q"
    " !p [bb4 c5 en5 g5]q& |")
cad.voice("lh").bars("!f [c1 c2]h. | rh !p [c2 g2 bb2 en3]q |")
cad.pedal("bar")
s.tempo_change("CADENZA", 1, 100)
s.ritardando("CADENZA", 2, 3, 56)

# ── RETURN: the theme in full chords ──
ret = s.section("RETURN")
ret.voice("rh").bars(
    "!f [c5 f5 ab5 c6]q. [db5 db6]e [c5 f5 ab5 c6]q |"
    " +ab6 [g5 c6 g6]h [f5 ab5 f6]q |"
    " [en5 g5 en6]q [f5 f6]q [g5 bb5 g6]q |"
    " [ab5 c6 ab6]h [g5 bb5 g6]q |"
    " [bb5 en6 bb6]q. [ab5 ab6]e [g5 g6]q |"
    " [f5 bb5 f6]h [en5 g5 bb5 en6]q |"
    " [f5 ab5 f6]q [ab5 c6 ab6]q [c6 f6 c7]q |"
    " [f5 ab5 c6 f6]q {c6 bb5 ab5 g5 f5 en5}q {db6 c6 bb5 ab5 g5 f5}q |"
    " cresc [eb5 g5 eb6]q. [f5 f6]e [eb5 g5 eb6]q |"
    " +c7 [bb5 db6 bb6]h [ab5 ab6]q |"
    " [g5 g6]q [ab5 c6 ab6]q [bb5 bb6]q |"
    " !ff [c6 eb6 ab6 c7]h {bb5 c6 db6 eb6 f6 g6}q |"
    " [db6 f6 bb6 db7]q. [c6 c7]e [bb5 db6 bb6]q |"
    " [ab5 c6 ab6]q [g5 g6]q [f5 ab5 f6]q |"
    " [en5 g5 bb5 en6]q [f5 f6]q [g5 bb5 g6]q |"
    " [f5 ab5 c6 f6]h. |")
ret_lh = [waltz(o, c) for _b, o, c in HARM]
ret_lh[11] = "!ff " + ret_lh[11]
ret.voice("lh").bars("!f " + bars(ret_lh))
ret.pedal("bar")
ret.rubato(0.03, phrase=4, shape="arch")

# ── CODA: stretto and chromatic octaves ──
coda = s.section("CODA")
RUN = ("c5s db5s dn5s eb5s en5s f5s gb5s gn5s ab5s an5s bb5s bn5s |"
       " c6s db6s dn6s eb6s en6s f6s gb6s gn6s ab6s an6s bb6s bn6s |")
coda.voice("rh").bars(
    "!ff [c5 c6]q [db5 db6]q [c5 c6]q |"
    " [en5 en6]q [f5 f6]q [en5 en6]q |"
    " [g5 g6]q [ab5 ab6]q [g5 g6]q |"
    " [bb5 bb6]q [c6 c7]q [bb5 bb6]q | " + octaves(RUN))
coda.voice("lh").bars(
    "!ff " + waltz("[f1 f2]", "f3 ab3 c4") + " | "
    + waltz("[c2 c3]", "en3 g3 bb3") + " | "
    + waltz("[c2 c3]", "en3 g3 bb3") + " | "
    + waltz("[c2 c3]", "en3 g3 bb3") + " | "
    + waltz("[c1 c2]", "en3 g3 bb3") + " | "
    + waltz("[c1 c2]", "en3 g3 bb3") + " |")
s.ritardando("CODA", 1, 7, 204)

fin = s.section("FINALE")
fin.voice("rh").bars(
    "!fff [f5 ab5 c6 f6]q rq [c5 en5 g5 c6]q |"
    " [f5 ab5 c6 f6]q rq [c5 en5 bb5 c6]q |"
    " [f5 ab5 c6 f6]q rq [f5 ab5 c6 f6]q |"
    " rq [c6 f6 ab6 c7]q [f6 ab6 c7 f7]q |"
    " [f5 ab5 c6 f6]q rh |")
fin.voice("lh").bars(
    "!fff [f1 f2]q rq [c2 c3]q |"
    " [f1 f2]q rq [c2 c3]q |"
    " [f1 f2]q rq [f1 f2]q |"
    " rq [f2 c3 f3]q [f2 f3]q |"
    " [f1 f2 c3 f3]q rh |")
fin.pedal(1)
s.tempo_change("FINALE", 1, 168)

s.arrange("INTRO THEME VARIATION EPISODE TRIO CADENZA RETURN CODA FINALE")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "horowitz_valse_brillante.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
