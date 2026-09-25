#!/usr/bin/env python3
"""Danse macabre on the Dies irae, in G minor. In the manner of Horowitz.

A fantasy in the line of Saint-Saens's Danse macabre as Liszt and then
Horowitz rewrote it for the piano, on original waltz themes and the
Dies irae chant. Midnight strikes twelve on a low D; Death tunes his
fiddle to the tritone; a skeletal waltz, its chattering middle strain
over a dominant pedal, then the tune in octaves; a variation of rattling
bones at the top of the keyboard; the tune marched in the bass under
off-beat chords; a lamenting second waltz in B-flat, sung and then set
for three hands. The chant enters lugubre over a chromatic lament bass,
returns as a fortissimo chorale, and is danced as a waltz. A fugato on
the waltz theme breaks into a cadenza of interlocking octaves; the
waltzes return, the second turned to a grandioso G major; at the climax
the chant thunders in the bass under hammered triplets, and a Presto
whirls until the cock crows and the dead scatter at dawn.

Built with scoremill's helpers: harmonize() voices the chant and the
reprise without parallel fifths or octaves against the bass,
double() writes the octaves, note_pitch() and note_name() move notes
by number, and transpose_chords() carries the lament to D minor."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import (NOTE_RE, Song, chord_pitches, double, harmonize,
                       note_name, note_pitch, transpose, transpose_chords)

KEY = "Gm"


def notes(frag, key=KEY):
    """(pitch, duration, marks) for each note or rest (pitch None) of a
    fragment whose notes all carry their octave."""
    out = []
    for tok in frag.split():
        m = NOTE_RE.match(tok)
        if m:
            p = None if m.group(1) == "r" else note_pitch(
                m.group(1) + (m.group(2) or "") + m.group(3), key)
            out.append((p, m.group(4), m.group(5) or ""))
    return out


def stacc(frag):
    """Staccato on every quarter and eighth, single or a chord, that is
    not a rest."""
    out, inside = [], False
    for tok in frag.split():
        inside = inside or tok.startswith("[")
        if inside:                         # a chord's members, then ']q'
            if tok.endswith(("]q", "]e")):
                tok += "'"
            inside = "]" not in tok
        else:
            m = NOTE_RE.match(tok)
            if (m and m.group(1) != "r" and m.group(4) in ("q", "e")
                    and "'" not in tok):
                tok += "'"
        out.append(tok)
    return " ".join(out)


def octave_bass(n, key=KEY):
    """A bass note with its octave below, or above where below would
    leave the keyboard."""
    p = note_pitch(n, key)
    lo = p - 12 if p - 12 >= 21 else p
    return f"[{note_name(lo, key)} {note_name(lo + 12, key)}]"


def waltz(bass, chord, mark="'"):
    return f"{bass}q [{chord}]q{mark} [{chord}]q{mark}"


def join(items):
    return " | ".join(items) + " |"


def dyn(items, marks):
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


# ── the themes ──
T1 = ["rq d5q d5q", "g5q f#5q g5q", "bb5q a5q g5q", "f#5h.",
      "rq c5q c5q", "eb5q d5q eb5q", "g5q f#5q eb5q", "d5h.",
      "rq d5q d5q", "g5q f#5q g5q", "d6q c6q bb5q", "a5q g5q f#5q",
      "g5q eb5q c5q", "a5q f#5q d5q", "bb4q a4q f#4q", "g4h."]
H1 = ["Gm", "Gm", "Gm", "D7", "Cm", "Cm", "D7", "D7",
      "Gm", "Gm", "Gm", "D7", "Cm", "D7", "D7", "Gm"]
CHATTER = ["d5e eb5e d5e c#5e d5e a4e", "d5e eb5e d5e c#5e d5e bb4e",
           "d5e eb5e d5e c#5e d5e c5e", "d5e f#5e eb5e d5e c5e bb4e",
           "a4e bb4e a4e g#4e a4e f#4e", "a4e c5e bb4e a4e g4e f#4e",
           "g4e a4e bb4e c5e d5e eb5e", "f#5e g5e a5e c6e d6q"]
HC = ["D", "D", "D", "D7", "D7", "D7", "Cm6", "D7"]
ROOT = {"Gm": ("g2", "d2"), "D7": ("d2", "a1"), "D": ("d2", "a1"),
        "Cm": ("c2", "g1"), "Cm6": ("c2", "g1")}
CHORD = {"Gm": "g3 bb3 d4", "D7": "f#3 a3 c4", "D": "f#3 a3 d4",
         "Cm": "g3 c4 eb4", "Cm6": "eb3 g3 a3"}
T2 = ["f5h d5q", "bb5h a5q", "ab5h g5q", "gb5h.", "f5h.", "g5h eb5q",
      "f5h eb5q", "c5h.", "f5h d5q", "bb5h a5q", "ab5h g5q", "gb5h.",
      "d6h bb5q", "c6h a5q", "g5h eb5q", "d5h."]
H2 = ["Bb", "Gm", "Eb7", "Ebm", "Bb/F", "Cm7", "F7", "F",
      "Bb", "Gm", "Eb7", "Ebm", "Bb/F", "F7", "F9", "Bb"]
DIES = ["bb4h.", "a4h.", "bb4h.", "g4h.", "a4h.", "f4h.", "g4h.", "g4h."]


def bass_of(h, i):
    """The waltz bass for bar i: the root, then the fifth."""
    return ROOT[h][i % 2]


s = Song(tempo=60, time="3/4", key=KEY, humanize=1, expressive=True,
         title="Danse macabre on the Dies irae", composer="after Horowitz")

# ── MINUIT: twelve strokes on D ──
mn = s.section("MINUIT")
mn.voice("rh").bars("!ppp [g4 bb4 d5]h.~ | [g4 bb4 d5]h.~ | [g4 bb4 d5]h.~ |"
                    " [g4 bb4 d5]h. |")
mn.voice("lh").bars("!p ([d1 d2]q> [d1 d2]q> [d1 d2]q> |)*4")
mn.pedal("bar")

# ── VIOLON: Death tunes his fiddle to the tritone ──
vn = s.section("VIOLON")
vn.voice("rh").bars(
    "!p [a4 eb5]h.&^ | [a4 eb5]q& [a4 eb5]q& rq | [a4 eb5]h.&^ |"
    " rq {d5 eb5 en5 f5 f#5 g5}q a5q | !mf [a5 eb6]h.&^ | rh. | rh. |")
vn.voice("lh").bars(
    "!pp [g1 d2]h. | rh. | [g1 d2]h. | rh. | [d1 a1]h. |"
    " !p " + waltz("g2", CHORD["Gm"]) + " | " + waltz("d2", CHORD["Gm"]) + " |")
vn.rubato(0.06, phrase=1, shape="cradle")
s.tempo_change("VIOLON", 6, 126)

# ── VALSE I: the tune, the chatter over the dominant, the tune in octaves ──
v1 = s.section("VALSE1")
v1.voice("rh").bars(join(
    dyn([stacc(m) for m in T1], {0: "!p", 8: "cresc", 12: "!mf"})
    + dyn([stacc(m) for m in CHATTER], {0: "!mp", 4: "cresc", 7: "!f"})
    + dyn([double(stacc(m), 7) for m in T1],
          {0: "!f", 8: "cresc", 12: "!ff"})))
v1.voice("lh").bars(join(
    dyn([waltz(bass_of(h, i), CHORD[h]) for i, h in enumerate(H1)],
        {0: "!p", 8: "cresc", 12: "!mf"})
    + dyn([waltz(bass_of(h, i), CHORD[h]) for i, h in enumerate(HC)],
          {0: "!mp", 4: "cresc", 7: "!f"})
    + dyn([waltz(octave_bass(bass_of(h, i)), CHORD[h], "'>")
           for i, h in enumerate(H1)], {0: "!f", 8: "cresc", 12: "!ff"})))
s.tempo_change("VALSE1", 1, 126)


# ── OS: the bones rattle at the top of the keyboard ──
def bones(frag):
    """Each note an octave up as a rattle of dry sixteenths."""
    out = []
    for p, d, _m in notes(frag):
        if p is None:
            out.append(f"r{d}")
            continue
        n = note_name(p + 12, KEY)
        out += [f"{n}s' rs"] * round(4 * {"q": 1, "h.": 3}[d] / 2)
    return " ".join(out)


DRY = {"Gm": "bb3 d4", "D7": "a3 c4", "Cm": "c4 eb4"}
os_ = s.section("OS")
os_.voice("rh").bars(join(dyn([bones(m) for m in T1],
                              {0: "!mp", 8: "cresc", 12: "!mf", 15: "!p"})))
os_.voice("lh").bars(join(dyn(
    [f"{bass_of(h, i)}e' re [{DRY[h]}]e' re [{DRY[h]}]e' re"
     for i, h in enumerate(H1)], {0: "!p", 8: "cresc", 12: "!mp", 15: "!p"})))
s.tempo_change("OS", 1, 144)

# ── TIERCES: the tune in double thirds and sixths, leggiero ──
ti = s.section("TIERCES")
pizz = join(dyn([f"{bass_of(h, i)}q' [{DRY[h]}]q' [{DRY[h]}]q'"
                 for i, h in enumerate(H1)],
                {0: "!p", 8: "cresc", 12: "!mf", 15: "!p"}))
ti.voice("rh").bars("!p " + stacc(harmonize(
    join(transpose(m, 12, key=KEY) for m in T1), " ".join(H1), key=KEY,
    voices=2, span=9, bass=pizz)))
ti.voice("lh").bars(pizz)
s.tempo_change("TIERCES", 1, 132)

# ── BASSE: the tune marched in the bass under off-beat chords ──
HIGH = {"Gm": "g5 bb5 d6", "D7": "f#5 a5 c6", "Cm": "g5 c6 eb6"}
low = [double(transpose(m, -24, key=KEY), 7) for m in T1]
bs = s.section("BASSE")
bs.voice("lh").bars(join(dyn([m.replace("q ", "q> ", 1) if m.startswith("[")
                              else m for m in low],
                             {0: "!f", 8: "cresc", 12: "!ff"})))
bs.voice("rh").bars(join(dyn(
    [f"re [{HIGH[h]}]e' re [{HIGH[h]}]e' re [{HIGH[h]}]e'" for h in H1],
    {0: "!mf", 8: "cresc", 12: "!f"})))
bs.pedal(1)
s.tempo_change("BASSE", 1, 132)

# ── VALSE II: the lament in B-flat, sung, then for three hands ──
W2 = {"Bb": ("bb1", "f3 bb3 d4"), "Gm": ("g1", "g3 bb3 d4"),
      "Eb7": ("eb2", "g3 bb3 db4"), "Ebm": ("eb2", "gb3 bb3 eb4"),
      "Bb/F": ("f1", "f3 bb3 d4"), "Cm7": ("c2", "g3 bb3 eb4"),
      "F7": ("f1", "f3 a3 eb4"), "F": ("f1", "f3 a3 c4"),
      "F9": ("f1", "a3 c4 eb4")}
# its middle strain: a chromatic descent through the circle of fifths
B2 = ["c6h bn5q", "bb5h a5q", "ab5h g5q", "f#5h.", "g5h f#5q", "f5h en5q",
      "eb5h d5q", "c5h."]
W2.update({"Cm": ("c2", "g3 c4 eb4"), "Gm/Bb": ("bb1", "g3 bb3 d4"),
           "Fm/Ab": ("ab1", "f3 ab3 c4"), "D7/F#": ("f#1", "f#3 a3 c4"),
           "Dm/F": ("f1", "f3 a3 d4"), "Cm/Eb": ("eb2", "g3 c4 eb4")})
HB2 = ["Cm", "Gm/Bb", "Fm/Ab", "D7/F#", "Gm", "Dm/F", "Cm/Eb", "F7"]
v2 = s.section("VALSE2", key="Bb")
sung = v2.voice("rh")
sung.bars(join(dyn(T2, {0: "!mf", 4: "dim", 5: "!mp", 8: "cresc",
                        12: "!f", 14: "dim", 15: "!p"})
               + dyn(B2, {0: "!mp", 2: "cresc", 4: "!mf", 6: "dim",
                          7: "!p"})))
sung.bars("!pp")
sung.harmony(" ".join(h.split("/")[0] for h in H2), octave=5,
             pattern="0 1 2 3 2 1", unit=0.25)
v2.voice("tenor").bars(join(["rh."] * 24 + dyn(
    [transpose(m, -12, key="Bb") for m in T2],
    {0: "!mf", 8: "cresc", 12: "!f", 14: "dim", 15: "!mp"})))
v2.voice("lh").bars(join(
    dyn([waltz(b, c, "") for b, c in (W2[h] for h in H2 + HB2)], {0: "!p"})
    + dyn([octave_bass(W2[h][0], "Bb") + "h." for h in H2], {0: "!p"})))
v2.pedal("bar")
v2.rubato(0.05, phrase=4, shape="cradle")
s.tempo_change("VALSE2", 1, 112)
s.ritardando("VALSE2", 39, 41, 90)

# ── SPECTRES: the lament in G minor, whispered in repeated notes ──
T2G_MINOR = ["d5h bb4q", "g5h f#5q", "f5h en5q", "eb5h.", "d5h.", "eb5h c5q",
             "d5h c5q", "a4h.", "d5h bb4q", "g5h f#5q", "f5h en5q", "eb5h.",
             "bb5h g5q", "a5h f#5q", "eb5h c5q", "bb4h."]
HS = ["Gm", "Eb", "C7", "Cm", "Gm/D", "Cm", "D7", "D", "Gm", "Eb", "C7", "Cm",
      "Gm/D", "D7", "D7", "Gm"]
WHISPER = {"Gm": ("g2", "bb3 d4"), "Eb": ("eb2", "bb3 eb4"),
           "C7": ("c2", "bb3 en4"), "Cm": ("c2", "c4 eb4"),
           "Gm/D": ("d2", "g3 bb3"), "D7": ("d2", "a3 c4"), "D": ("d2", "a3 d4")}


def whisper(frag):
    """Each note repeated in dry staccato eighths for its length."""
    out = []
    for p, d, _m in notes(frag):
        out += [note_name(p, KEY) + "e'"] * round({"q": 2, "h": 4, "h.": 6}[d])
    return " ".join(out)


sp = s.section("SPECTRES")
sp.voice("rh").bars(join(dyn([whisper(m) for m in T2G_MINOR],
                             {0: "!pp", 8: "cresc", 12: "!mp", 14: "dim",
                              15: "!ppp"})))
sp.voice("lh").bars(join(dyn(
    [f"{WHISPER[h][0]}e' re [{WHISPER[h][1]}]e' re [{WHISPER[h][1]}]e' re"
     for h in HS], {0: "!pp", 8: "cresc", 12: "!mp", 14: "dim", 15: "!ppp"})))
sp.soft()
s.tempo_change("SPECTRES", 1, 152)

# ── LUGUBRE: the Dies irae over a chromatic lament bass ──
chant = join(DIES)
LAMENT = "Gm D/F# Gm/F C/E F7/Eb Bb/D D7sus4 Gm"
lament_bass = join(f"{b}h." for b in ("gn2", "f#2", "fn2", "en2", "eb2",
                                      "dn2", "dn2", "gn1"))
chant_d = transpose(chant, 7, key=KEY)            # the answer in D minor
lament_d = transpose_chords(LAMENT, 7)
lament_bass_d = transpose(lament_bass, 7, key=KEY)
lg = s.section("LUGUBRE")
lg.voice("chant").bars(
    "!pp " + harmonize(chant, LAMENT, key=KEY, bass=lament_bass)
    + " cresc " + harmonize(chant_d, lament_d, key="Dm", bass=lament_bass_d)
    + " !mf")
lg.voice("bell", vel=24).bars("!ppp " + join(["d6q' rh"] * 16))
lg.voice("bass").bars("!pp " + lament_bass + " cresc " + lament_bass_d
                      + " !mf")
lg.pedal("bar")
lg.soft()
lg.rubato(0.04, phrase=2, shape="cradle")
s.tempo_change("LUGUBRE", 1, 50)

# ── DIES IRAE: the chant as a chorale, then danced ──
# The chant note is the third or the root of its chord, not the fifth,
# so the chant and the bass never move in fifths.
DIES_SYM = "Gm F Bb Eb F Dm D7sus4 Gm"
DIES_ROOT = ["g1", "f1", "bb1", "eb1", "f1", "d2", "d2", "g1"]
DIES_CHORD = {"Gm": "g3 bb3 d4", "F": "f3 a3 c4", "Eb": "g3 bb3 eb4",
              "Bb": "f3 bb3 d4", "Dm": "f3 a3 d4", "D7sus4": "g3 a3 c4"}
top = transpose(chant, 12, key=KEY)
organ = join(octave_bass(b) + "h." for b in DIES_ROOT)
danced = join(waltz(octave_bass(b), DIES_CHORD[h])
              for b, h in zip(DIES_ROOT, DIES_SYM.split()))
di = s.section("DIES")
di.voice("rh").bars(
    "!ff " + harmonize(top, DIES_SYM, key=KEY, voices=4, bass=organ)
    + " " + harmonize(top, DIES_SYM, key=KEY, voices=3,
                      bass=danced).replace("h.", "h.>"))
di.voice("lh").bars("!ff " + organ + " " + danced)
di.pedal("bar")
s.tempo_change("DIES", 1, 60)
s.tempo_change("DIES", 9, 132)

# ── FUGATO on the waltz ──
SUBJ = ["d4q g4q f#4e g4e", "bb4q a4q g4q", "f#4e g4e a4e bb4e c5e a4e",
        "bb4e a4e g4e f#4e g4q"]
ANS = ["a4q d5q c#5e d5e", "f5q en5q d5q", "c#5e d5e en5e f5e g5e en5e",
       "f5e en5e d5e c#5e d5q"]
COUNTER = ["f4e en4e d4e f4e en4e f4e", "a4e g4e a4e bb4e f4e en4e",
           "a4q g4q c#5q", "d5q f4q d4q"]
D7_TOP = "[f#4 a4 c5 d5]"
fg = s.section("FUGATO")
fg.voice("soprano").bars(join(
    ["rh."] * 4 + dyn(ANS, {0: "!mf"})
    + dyn([transpose(c, 5, key=KEY) for c in COUNTER], {0: "!f"})
    + [f"!ff {D7_TOP}h.>", f"{D7_TOP}h.^"]))
fg.voice("alto").bars(join(
    dyn(SUBJ, {0: "!mf"}) + COUNTER
    + ["!f d4h.", "g4q f#4q g4q", "a4h.", "d5q g4q d4q", "rh.", "rh."]))
fg.voice("bass").bars(join(
    ["rh."] * 8 + dyn([transpose(x, -12, key=KEY) for x in SUBJ], {0: "!f"})
    + ["!ff [d2 a2]h.>", "[d1 d2]h.^"]))
s.tempo_change("FUGATO", 1, 144)

# ── CADENZA: interlocking octaves, a whirlwind, the fiddle again ──
fall = " ".join(f"[{note_name(p - 12, KEY)} {note_name(p, KEY)}]s"
                for p in range(86, 70, -1))
rise = " ".join(f"[{note_name(p, KEY)} {note_name(p + 12, KEY)}]s"
                for p in range(31, 47))
run = " ".join(note_name(p, KEY) for p in range(87, 69, -1))
run = " ".join("{" + " ".join(run.split()[k:k + 6]) + "}q"
               for k in range(0, 18, 6))
cz = s.section("CADENZA", time="4/4")
cz.voice("rh").bars(
    "!ff " + fall + " |"
    " {g4 a4 bb4 c5 d5 eb5 f#5}q {g5 a5 bb5 c6 d6 eb6 f#6}q"
    " {g6 f#6 eb6 d6 c6 bb5 a5}q {g5 f#5 eb5 d5 c5 bb4 a4}q |"
    " !f d6w% | !ff [a4 eb5]h&^ [a5 eb6]h&^ | dim " + run + " !p an4q^ |")
cz.voice("lh").bars(
    "!ff " + rise + " | [g1 d2 g2]w& | !f (d2s a2s)*8 |"
    " !ff [d1 d2]h^ [d1 a1 d2]h^ | dim rh. !p [d2 d3]q^ |")
cz.pedal("bar")
cz.rubato(0.06, phrase=1, shape="cradle")
s.tempo_change("CADENZA", 1, 72)

# ── REPRISE I: the waltz fortissimo, in full chords an octave up ──
rp = s.section("REPRISE1")
waltz_lh = [waltz(octave_bass(bass_of(h, i)), CHORD[h], "'>")
            for i, h in enumerate(H1)]
rp.voice("rh").bars(
    "!ff " + harmonize(join(transpose(m, 12, key=KEY) for m in T1),
                       " ".join(H1), key=KEY, voices=4, bass=join(waltz_lh))
    + " " + join(dyn([double(stacc(m), 7) for m in CHATTER],
                     {0: "!f", 4: "cresc", 7: "!fff"})))
rp.voice("lh").bars(join(
    dyn(waltz_lh, {0: "!ff"})
    + dyn([waltz(octave_bass(bass_of(h, i)), CHORD[h], "'>")
           for i, h in enumerate(HC)], {0: "!f", 4: "cresc", 7: "!fff"})))
rp.pedal(1)
s.tempo_change("REPRISE1", 1, 144)


# ── REPRISE II: the lament turned to G major, grandioso ──
def octave_fill(frag, sym, key):
    """Each note in octaves with a chord tone between: [p, inner, p+12]."""
    pcs = {p % 12 for p in chord_pitches(sym)}
    out = []
    for p, d, marks in notes(frag, key):
        inner = next(x for x in range(p + 9, p, -1) if x % 12 in pcs)
        out.append("[" + " ".join(note_name(x, key)
                                  for x in (p, inner, p + 12)) + "]" + d + marks)
    return " ".join(out)


T2G = [transpose(m, -3, key="Bb") for m in T2]
H2G = transpose_chords(" ".join(H2), -3).split()
rg = s.section("REPRISE2", key="G")
rg.voice("rh").bars(join(dyn([octave_fill(m, h, "G") for m, h in zip(T2G, H2G)],
                             {0: "!ff", 8: "cresc", 12: "!fff", 14: "dim",
                              15: "!ff"})))
sweep = rg.voice("lh", vel=66)
sweep.harmony(" ".join(h.split("/")[0] for h in H2G), octave=2,
              pattern="0 1 2 3 2 1", unit=0.5)
rg.pedal("bar")
rg.rubato(0.04, phrase=4, shape="arch")
s.tempo_change("REPRISE2", 1, 104)
s.ritardando("REPRISE2", 15, 17, 88)

# ── CLIMAX: the chant thunders in the bass under hammered triplets ──
HAMMER = ["bb4 d5 g5", "c5 d5 f#5", "bb4 d5 g5", "g4 c5 eb5", "a4 d5 f#5",
          "f4 bb4 d5", "g4 bb4 eb5", "g4 bb4 d5 g5"]
DIES_LOW = ["[bb0 bb1]", "[a0 a1]", "[bb0 bb1]", "[g1 g2]", "[a0 a1]",
            "[f1 f2]", "[g1 g2]", "[g1 g2]"]
up = " ".join(f"[{note_name(p, KEY)} {note_name(p + 12, KEY)}]s"
              for p in range(74, 86))
down = " ".join(f"[{note_name(p - 12, KEY)} {note_name(p, KEY)}]s"
                for p in range(50, 38, -1))
D7_CRASH = "[d5 f#5 a5 c6 d6]"
cl = s.section("CLIMAX")
cl.voice("rh").bars(join(
    dyn([" ".join(f"{{[{c}] [{c}] [{c}]}}q" for _ in range(3)) for c in HAMMER],
        {0: "!fff"})
    + ["cresc " + up, f"!fff {D7_CRASH}q> {D7_CRASH}q> {D7_CRASH}q>",
       f"{D7_CRASH}h.&^", "rh.^"]))
cl.voice("lh").bars(join(
    dyn([f"{b}h.>" for b in DIES_LOW], {0: "!fff"})
    + ["cresc " + down, "!fff [d1 d2]q> [d1 d2]q> [d1 d2]q>",
       "[d1 a1 d2]h.&^", "rh.^"]))
cl.pedal(1)
s.tempo_change("CLIMAX", 1, 116)
s.ritardando("CLIMAX", 11, 13, 90)


# ── PRESTO: the waltz whirls, until the cock crows ──
def below(p, sym, gap=3):
    pcs = {x % 12 for x in chord_pitches(sym)}
    return next(x for x in range(p - gap, p - 13, -1) if x % 12 in pcs)


def whirl(frag, sym):
    """Each note on its beat, the chord tones under it in sixteenths."""
    out = []
    for p, d, _m in notes(frag):
        n = round({"q": 1, "h.": 3}[d] * 4)
        if p is None:
            out.append(f"r{d}")
            continue
        x1 = below(p, sym)
        x2 = below(x1, sym)
        out += [note_name(q, KEY) + "s" for q in ([p, x1, x2, x1] * 3)[:n]]
    return " ".join(out)


pr = s.section("PRESTO")
pr.voice("rh").bars(join(dyn(
    [whirl(transpose(m, 12, key=KEY), h) for m, h in zip(T1[:15], H1)]
    + ["[d5 g5 bb5 d6]q> rh^"], {0: "!f", 8: "cresc", 12: "!ff", 15: "!fff"})))
pr.voice("lh").bars(join(dyn(
    [waltz(octave_bass(bass_of(h, i)), CHORD[h]) for i, h in enumerate(H1[:15])]
    + ["[g1 g2]q> rh^"], {0: "!f", 8: "cresc", 12: "!ff", 15: "!fff"})))
pr.pedal(1)
s.tempo_change("PRESTO", 1, 168)

# ── AUBE: the cock crows and the dead scatter ──
ab = s.section("AUBE")
ab.voice("rh").bars(
    "!p rh +f#6 g6e. d6s | g6q' rh | !pp rq d5q' d5q' | g5q' rh |"
    " rq f#4q' rq | g4q' rh | !ppp " + join(T2G_MINOR[:4])
    + " [a4 eb5]h.&^ | rh. |")
ab.voice("lh").bars(
    "!pp ped [d2 a2]h.~ | [d2 a2]h. | lift [g2 d3]q' rh | [c3 eb3]q' rh |"
    " [d2 a2]q' rh | [g2 d3]q' rh | ped [g2 d3 bb3]h. | ped [eb2 bb2 g3]h. |"
    " ped [c2 g2 en3]h. | ped [c2 g2 eb3]h. | ped [d2 a2]h.^ |"
    " lift [g1 d2 g2]q' rh^ |")
ab.soft()
s.tempo_change("AUBE", 1, 54)
s.ritardando("AUBE", 7, 11, 44)

s.arrange("MINUIT VIOLON VALSE1 OS TIERCES BASSE VALSE2 SPECTRES LUGUBRE DIES"
          " FUGATO CADENZA REPRISE1 REPRISE2 CLIMAX PRESTO AUBE")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "horowitz_danse_macabre.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
