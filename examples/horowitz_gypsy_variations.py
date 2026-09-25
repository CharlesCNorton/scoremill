#!/usr/bin/env python3
"""Variations on a Gypsy Dance. In the manner of Horowitz.

An original habanera theme in E Phrygian, taken through variations of
rising brilliance in the spirit of Horowitz's Carmen Variations:
parallel sixths; a tenor melody under a repeated-note tremolo (the
three-hand effect); an Adagio nocturne in E major; double thirds; a
music-box scherzando at the top of the keyboard; a Presto of full chords
over driving octaves; and a coda of Andalusian cadences, chromatic
octaves in contrary motion, and the Phrygian F-E hammered home.

Most variations are generated from the theme by small voicing helpers,
the same way a transcriber elaborates a tune."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song

LETTER = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
ACCS = {"": 0, "n": 0, "#": 1, "b": -1, "##": 2, "bb": -2}
NAMES = ["cn", "c#", "dn", "d#", "en", "fn", "f#", "gn", "g#", "an", "a#", "bn"]
NOTE = re.compile(r"^([a-g])(##|bb|#|b|n)?(\d)([whqest]\.?)?([~>'_^&]*)$")
SIXTEENTHS = {"s": 1, "e": 2, "e.": 3, "q": 4, "q.": 6, "h": 8}
HARMONIC = {9, 11, 0, 2, 4, 5, 8}      # A B C D E F G#
NATURAL = {9, 11, 0, 2, 4, 5, 7}       # A B C D E F G


def to_midi(letter, acc, octave):
    return 12 * (int(octave) + 1) + LETTER[letter] + ACCS[acc or ""]


def nm(m):
    """A note name with an explicit accidental, so no key applies."""
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def step(m, k, pcs):
    """The pitch k scale steps from m within the pitch classes pcs."""
    scale = [p for p in range(12, 120) if p % 12 in pcs]
    i = min(range(len(scale)), key=lambda j: abs(scale[j] - m))
    return scale[i + k]


def voiced(frag, fn, mark=""):
    """Replace every single note with the chord fn(midi) returns."""
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        l, a, o, d, marks = m.groups()
        ps = sorted(set(fn(to_midi(l, a, o))))
        body = nm(ps[0]) if len(ps) == 1 else "[" + " ".join(map(nm, ps)) + "]"
        out.append(body + (d or "") + marks + mark)
    return " ".join(out)


def double_thirds(frag, pcs):
    """Sixteenths in thirds that trill between each melody note and its
    upper neighbor, keeping the melody's rhythm on the beat."""
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if not m:
            out.append(tok)
            continue
        l, a, o, d, _marks = m.groups()
        x = to_midi(l, a, o)
        for i in range(SIXTEENTHS[d]):
            y = x if i % 2 == 0 else step(x, 1, pcs)
            out.append(f"[{nm(step(y, -2, pcs))} {nm(y)}]s")
    return " ".join(out)


def join(items):
    return " | ".join(items) + " |"


THEME = [
    "+f5 e5e. f5s e5e d5e", "c5e. b4s c5e d5e", "e5e. f5s g#5e a5e",
    "g#5e f5e e5q", "+b5 a5e. g#5s a5e b5e", "c6e. b5s a5e g5e",
    "f5e. e5s f5e a5e", "+a5 g#5q e5q", "e5e a5e c6e e6e",
    "f6e. e6s d6e c6e", "b5e. c6s d6e b5e", "c6q g5q",
    "a5e. g5s f5e a5e", "g#5e. f5s e5e d5e", "c6e. b5s a5e f5e", "e5q rq"]
PLAIN = [re.sub(r"\+\S+ ", "", t) for t in THEME]
HARM = ["E", "Am", "E7", "E", "Am", "G", "F", "E",
        "Am", "Dm", "G7", "C", "F", "E7", "F", "E"]
PCS = [HARMONIC if h in ("E", "E7") or (h == "Am" and i < 8) else NATURAL
       for i, h in enumerate(HARM)]
HAB = {  # bass, bass octave, fifth, chord
    "E": ("e2", "[e1 e2]", "b2", "g#3 b3"), "Am": ("a1", "[a1 a2]", "e2", "c3 e3"),
    "E7": ("e2", "[e1 e2]", "b2", "g#3 d4"), "G": ("g1", "[g1 g2]", "d2", "b2 d3"),
    "F": ("f1", "[f1 f2]", "c2", "a2 c3"), "Dm": ("d2", "[d1 d2]", "a2", "f3 a3"),
    "G7": ("g1", "[g1 g2]", "d2", "b2 f3"), "C": ("c2", "[c1 c2]", "g2", "e3 g3"),
}


def habanera(h, octave=False, chord=True):
    bass, boct, fifth, ch = HAB[h]
    b = boct if octave else bass
    if not chord:
        return f"{b}e. {fifth}s {bass}e {fifth}e"
    return f"{b}e. {fifth}s [{ch}]e [{ch}]e"


def dyn(items, marks):
    """Prefix dynamics to bars: marks maps bar index -> token."""
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


s = Song(tempo=88, time="2/4", key="Am", humanize=1, expressive=True)

# ── INTRO: the Andalusian cadence, strummed ──
intro = s.section("INTRO")
intro.voice("rh").bars(
    "!f [e4 a4 c5 e5]q& [e4 a4 c5 e5]e& [e4 a4 c5 e5]e& |"
    " [d4 g4 b4 d5]q& [d4 g4 b4 d5]e& [d4 g4 b4 d5]e& |"
    " [c4 f4 a4 c5]q& [c4 f4 a4 c5]e& [c4 f4 a4 c5]e& |"
    " [b3 e4 g#4 b4 e5]h& | rh | rh |")
intro.voice("lh").bars(
    "!f [a1 a2]q [a1 a2]q | [g1 g2]q [g1 g2]q | [f1 f2]q [f1 f2]q |"
    " [e1 e2]h | !p e2e. e2s e2e e2e | e2e. e2s e2e b1e |")
intro.pedal(1)
s.tempo_change("INTRO", 1, 80)
s.tempo_change("INTRO", 4, 46)
s.tempo_change("INTRO", 5, 88)

# ── THEME ──
th = s.section("THEME")
th.voice("rh").bars(join(dyn(THEME, {0: "!mp", 8: "cresc", 11: "!mf",
                                     12: "dim", 15: "!p"})))
th.voice("lh").bars("!p " + join([habanera(h) for h in HARM]))
th.pedal("bar")
th.rubato(0.03, phrase=2)

# ── I: parallel sixths ──
v1 = s.section("VAR1")
sixths = [voiced(PLAIN[i], lambda x, p=PCS[i]: [step(x, -5, p), x], "'")
          for i in range(16)]
sixths[15] = "[g#4 b4 e5]q rq"
v1.voice("rh").bars(join(dyn(sixths, {0: "!mf", 8: "cresc", 11: "!f",
                                      12: "dim", 15: "!mf"})))
v1.voice("lh").bars("!mp " + join([habanera(h) for h in HARM]))
v1.pedal("bar")
s.tempo_change("VAR1", 1, 96)

# ── II: tenor melody under a repeated-note tremolo ──
v2 = s.section("VAR2")
TREM = {"E": ("e6", "b5"), "Am": ("e6", "c6"), "E7": ("d6", "b5"),
        "G": ("d6", "b5"), "F": ("c6", "a5"), "Dm": ("d6", "a5"),
        "G7": ("d6", "b5"), "C": ("e6", "c6")}


def tremolo(h):
    hi, lo = TREM[h]
    beat = f"{{{hi} {hi} {lo} {hi} {hi} {lo}}}q"
    return beat + " " + beat


v2.voice("rh").bars(join(dyn([tremolo(h) for h in HARM],
                             {0: "!p", 8: "cresc", 11: "!mf", 12: "dim",
                              15: "!p"})))
v2.voice("tenor").bars(join(dyn([voiced(t, lambda x: [x - 24, x - 12])
                                 for t in PLAIN],
                                {0: "!mf", 8: "cresc", 11: "!f", 12: "dim",
                                 15: "!mf"})))
v2.voice("bass").bars("!mp " + join([habanera(h, chord=False)
                                     for h in HARM]))
v2.pedal("bar")
s.tempo_change("VAR2", 1, 92)

# ── III: Adagio nocturne in E major ──
v3 = s.section("VAR3", key="E")
NOCT = ["en5e. f#5s en5e d#5e", "c#5e. bn4s c#5e d#5e",
        "en5e. f#5s g#5e an5e", "g#5e f#5e +f#5 en5q",
        "an5e. g#5s an5e bn5e", "c#6e. bn5s an5e g#5e",
        "f#5e. en5s f#5e an5e", "g#5q en5q",
        "en5e an5e c#6e en6e", "f#6e. en6s d#6e c#6e",
        "bn5e. c#6s d#6e bn5e", "c#6q g#5q",
        "an5e. g#5s f#5e an5e", "g#5e. f#5s en5e d#5e",
        "c#6e. bn5s an5e f#5e", "en5h"]
v3.voice("rh").bars(join(dyn(NOCT, {0: "!p", 8: "cresc", 9: "!mf",
                                    12: "dim", 15: "!pp"})))
ARP = {"E": ["en2", "bn2", "en3", "g#3"], "C#m7": ["c#2", "g#2", "bn2", "en3"],
       "B7": ["bn1", "f#2", "an2", "d#3"], "A": ["an1", "en2", "an2", "c#3"],
       "F#m7": ["f#1", "c#2", "en2", "an2"], "B": ["bn1", "f#2", "bn2", "d#3"],
       "C#m": ["c#2", "g#2", "c#3", "en3"], "A6": ["an1", "en2", "f#2", "c#3"],
       "B13": ["bn1", "an2", "d#3", "g#3"], "B9": ["bn1", "f#2", "an2", "c#3"]}
NOCT_H = ["E", "C#m7", "B7", "E", "A", "F#m7", "B7", "E",
          "A", "F#m7", "B", "C#m", "A6", "B13", "B9", "E"]


def sextuplets(h):
    t = ARP[h]
    beat = f"{{{t[0]} {t[1]} {t[2]} {t[3]} {t[2]} {t[1]}}}q"
    return beat + " " + beat


v3.voice("lh").bars("!pp " + join([sextuplets(h) for h in NOCT_H]))
v3.pedal("bar")
v3.rubato(0.06, phrase=2, shape="cradle")
s.tempo_change("VAR3", 1, 58)
s.ritardando("VAR3", 15, 17, 42)

# ── IV: double thirds ──
v4 = s.section("VAR4")
v4.voice("rh").bars(join(dyn([double_thirds(PLAIN[i], PCS[i])
                              for i in range(16)],
                             {0: "!mf", 8: "cresc", 11: "!f", 12: "dim",
                              15: "!mf"})))
v4.voice("lh").bars("!mf " + join([habanera(h, octave=True) for h in HARM]))
v4.pedal(1)
s.tempo_change("VAR4", 1, 100)

# ── V: music box, two octaves up the keyboard ──
v5 = s.section("VAR5")
v5.voice("rh").bars(join(dyn([voiced(t, lambda x: [x + 12], "'")
                              for t in PLAIN],
                             {0: "!p", 8: "cresc", 11: "!mp", 12: "dim",
                              15: "!pp"})))
BOX = {"E": "g#4 b4 e5", "Am": "a4 c5 e5", "E7": "g#4 b4 d5",
       "G": "g4 b4 d5", "F": "a4 c5 f5", "Dm": "a4 d5 f5",
       "G7": "g4 b4 f5", "C": "g4 c5 e5"}
v5.voice("lh").bars("!pp " + join([f"[{BOX[h]}]e' re [{BOX[h]}]e' re"
                                   for h in HARM]))
v5.soft()
s.tempo_change("VAR5", 1, 104)

# ── VI: Presto, full chords over driving octaves ──
v6 = s.section("VAR6")
presto = [voiced(PLAIN[i], lambda x, p=PCS[i]: [step(x, -5, p), x, x + 12])
          for i in range(16)]
presto[15] = "[e5 g#5 b5 e6]q> rq"
v6.voice("rh").bars(join(dyn(presto, {0: "!f", 8: "cresc", 11: "!ff"})))
DRIVE = {"E": ("[e1 e2]", "[b1 b2]", "g#3 b3 e4"),
         "Am": ("[a1 a2]", "[e2 e3]", "e3 a3 c4"),
         "E7": ("[e1 e2]", "[b1 b2]", "g#3 b3 d4"),
         "G": ("[g1 g2]", "[d2 d3]", "g3 b3 d4"),
         "F": ("[f1 f2]", "[c2 c3]", "a3 c4 f4"),
         "Dm": ("[d1 d2]", "[a1 a2]", "a3 d4 f4"),
         "G7": ("[g1 g2]", "[d2 d3]", "g3 b3 f4"),
         "C": ("[c1 c2]", "[g1 g2]", "g3 c4 e4")}
v6.voice("lh").bars("!f " + join([f"{DRIVE[h][0]}e [{DRIVE[h][2]}]e'"
                                  f" {DRIVE[h][1]}e [{DRIVE[h][2]}]e'"
                                  for h in HARM]))
v6.pedal(1)
s.tempo_change("VAR6", 1, 138)

# ── CODA ──
ANDALUSIAN = [("b", "c e a c", "a1 a2", "e2 a2 c3"),
              ("a", "b d g b", "g1 g2", "d2 g2 b2"),
              ("g", "a c f a", "f1 f2", "c2 f2 a2"),
              ("f", "g# b e g#", "e1 e2", "b1 e2 g#2")]


def cadence_bars(octave, dyn_tok):
    rh, lh = [], []
    for grace, chord, boct, lchord in ANDALUSIAN:
        tones = chord.split()
        # every chord tone sits in `octave` except the top, an octave up;
        # the flick below the chord is a step under its lowest tone
        spread = [f"{t}{octave}" for t in tones[:-1]] + [f"{tones[-1]}{octave + 1}"]
        rh.append(f"+{grace}{octave} [{' '.join(spread)}]q& "
                  f"[{' '.join(spread[:3])}]q'")
        lh.append(f"[{boct}]e [{lchord}]e' [{boct}]e [{lchord}]e'")
    rh[0] = dyn_tok + " " + rh[0]
    lh[0] = dyn_tok + " " + lh[0]
    return rh, lh


c1 = s.section("CODA1")
rh_a, lh_a = cadence_bars(5, "!f")
rh_b, lh_b = cadence_bars(6, "!ff")
c1.voice("rh").bars(join(rh_a + rh_b))
c1.voice("lh").bars(join(lh_a + lh_b))
c1.pedal(1)
s.tempo_change("CODA1", 1, 132)

c2 = s.section("CODA2")
up = [nm(76 + i) for i in range(16)]           # E5 rising chromatically
down = [nm(52 - i) for i in range(16)]         # E3 falling chromatically
run_rh = " ".join(f"[{u} {nm(76 + i + 12)}]s" for i, u in enumerate(up))
run_lh = " ".join(f"[{nm(52 - i - 12)} {d}]s" for i, d in enumerate(down))
rh_run = run_rh.split()
lh_run = run_lh.split()
F_CH, E_CH = "[f5 a5 c6 f6]", "[e5 g#5 b5 e6]"
c2.voice("rh").bars(
    "!ff " + " ".join(rh_run[:16]) + " | " + " ".join(rh_run[16:])
    + " | !fff " + F_CH + "q& rq | " + E_CH + "q& rq |"
    f" {F_CH}e {E_CH}e {F_CH}e {E_CH}e | {F_CH}e {E_CH}e {F_CH}e {E_CH}e |"
    " [e4 g#4 b4 e5 g#5 b5 e6]q& rq | rh |")
c2.voice("lh").bars(
    "!ff " + " ".join(lh_run[:16]) + " | " + " ".join(lh_run[16:])
    + " | !fff [f1 f2 c3 f3]q rq | [e1 e2 b2 e3]q rq |"
    " [f1 f2]e [e1 e2]e [f1 f2]e [e1 e2]e | [f1 f2]e [e1 e2]e [f1 f2]e [e1 e2]e |"
    " [e1 e2 b2 e3]q& rq | rh |")
c2.pedal(1)
s.tempo_change("CODA2", 1, 144)
s.tempo_change("CODA2", 3, 108)
s.ritardando("CODA2", 5, 8, 84)

s.arrange("INTRO THEME VAR1 VAR2 VAR3 VAR4 VAR5 VAR6 CODA1 CODA2")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "horowitz_gypsy_variations.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
