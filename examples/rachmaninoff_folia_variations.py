#!/usr/bin/env python3
"""Variations on La Folia in D minor. In the manner of Rachmaninoff.

The old Spanish ground Rachmaninoff chose for his Corelli Variations,
carrying an original sarabande theme through eleven variations: a
division over a walking bass; compound sixteenths; a minuet with trills;
a chorale with the pedal notated beat by beat; a toccata of triplets
traded between the hands; agitato octaves over surging arpeggios; a
nocturne over quintuplets under the soft pedal; and a three-voice
fugato. An intermezzo a tempo rubato turns to D-flat major, where the
theme returns inverted and in the major, as in the eighteenth
variation of the Paganini Rhapsody; then a variation alla spagnola in
hemiolas, a climax with the theme in the bass under hammered chords,
and a coda that fades to ppp.

The variations are generated from the theme by voicing helpers, as a
transcriber elaborates a tune; the fugato, the intermezzo, and the coda
are written out."""
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


def midi(l, a, o):
    """Pitch of a written note in D minor: a plain b is B-flat."""
    alter = ACCS[a] if a else (-1 if l == "b" else 0)
    return 12 * (int(o) + 1) + LETTER[l] + alter


def nm(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def notes(frag):
    """(pitch, duration, marks) for each note of a fragment."""
    out = []
    for tok in frag.split():
        m = NOTE.match(tok)
        if m:
            out.append((midi(*m.group(1, 2, 3)), m.group(4), m.group(5) or ""))
    return out


def below(m, symbol, gap=3):
    """The highest tone of `symbol` at least `gap` semitones under m."""
    pcs = {p % 12 for p in chord_pitches(symbol)}
    return next(p for p in range(m - gap, m - 13, -1) if p % 12 in pcs)


def voiced(frag, fn, mark=""):
    """Replace every single note with the chord fn(pitch, duration)."""
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
    """Prefix a dynamic (or pedal) token to chosen bars."""
    items = list(items)
    for i, tok in marks.items():
        items[i] = tok + " " + items[i]
    return items


# ── the theme and its ground ──
THEME = ["a4q d5q. e5e", "f5q e5q. d5e", "c#5q d5q. a4e", "b4q c5q. g4e",
         "a4q f5q. e5e", "c5q g5q. f5e", "e5q d5q. f5e", "e5h.",
         "a5q d6q. c6e", "b5q a5q. g5e", "f5q a5q. d6e", "e6q c6q. b5e",
         "a5q f6q. e6e", "d6q c6q. b5e", "a5q g5q. e5e", "d5h."]
HARM = ["Dm", "A7", "Dm", "C7", "F", "C", "Dm", "A",
        "Dm", "A7", "Dm", "C7", "F", "C7", "A7", "Dm"]
OCT = {"Dm": "[d2 d3]", "A7": "[a1 a2]", "A": "[a1 a2]", "C7": "[c2 c3]",
       "C": "[c2 c3]", "F": "[f1 f2]"}
TENOR = {"Dm": "f3 a3 d4", "A7": "e3 g3 c#4", "A": "e3 a3 c#4",
         "C7": "e3 g3 bb3", "C": "e3 g3 c4", "F": "f3 a3 c4"}
# Two walking basses through the ground, a quarter a step. GROUND is set
# against the division's eighths so that no two samples in a row form the
# same perfect interval; WALK carries the minuet.
GROUND = ["d3 f3 bb2", "a2 c#3 e3", "a2 d3 f3", "e3 c3 bb2", "f2 a2 c3",
          "e3 c3 g2", "a2 f3 d3", "e3 a2 c#3", "d3 f3 a3", "g3 e3 c#3",
          "d3 c3 bb2", "c3 e3 g3", "f3 a3 c4", "bb3 e3 c3", "a2 c#3 g2",
          "f2 a2 d2"]
WALK = ["d3 e3 f3", "e3 c#3 a2", "d3 c3 bb2", "c3 e3 g3", "f3 e3 d3",
        "c3 bb2 g2", "d3 f3 a3", "a2 c#3 e3", "d3 c3 bb2", "a2 g2 f2",
        "d2 f2 a2", "c3 bb2 g2", "f2 a2 c3", "e2 g2 c3", "a2 e2 c#2",
        "d2 a1 d2"]


def walk_steps(i, octaves=False, mark="", line=GROUND):
    """The three quarter-note tokens of bar i of a walking bass, single
    or in octaves."""
    out = []
    for n in line[i].split():
        p = midi(n[0], n[1:-1], n[-1])
        out.append((f"[{nm(p - 12)} {nm(p)}]" if octaves else nm(p))
                   + "q" + mark)
    return out


def walk(i, octaves=False, mark="", line=GROUND):
    return " ".join(walk_steps(i, octaves, mark, line))


s = Song(tempo=72, time="3/4", key="Dm", humanize=1, expressive=True,
         title="Variations on La Folia", composer="after Rachmaninoff")

# ── THEME: a sarabande, the weight on the second beat ──
th = s.section("THEME")
th.voice("rh").bars(join(dyn(
    [voiced(m, lambda p, d, h=h: [below(p, h), p] if d in ("q.", "h.")
            else [p]) for m, h in zip(THEME, HARM)],
    {0: "!p", 8: "cresc", 12: "!mf", 13: "dim", 15: "!p"})))
th.voice("lh").bars(join(dyn([f"{OCT[h]}q [{TENOR[h]}]h" for h in HARM],
                             {0: "!p", 8: "cresc", 12: "!mf", 13: "dim",
                              15: "!p"})))
th.pedal("bar")
th.rubato(0.04, phrase=4, shape="arch")
s.ritardando("THEME", 15, 17, 58)

# ── I: a division in eighths over the walking bass ──
DIVISION = ["a4e f4e d5e c#5e d5e e5e", "f5e g5e e5e c#5e d5e e5e",
            "c#5e e5e d5e f5e a4e g4e", "b4e g4e c5e e5e g4e b4e",
            "a4e c5e f5e a5e e5e d5e", "c5e e5e g5e b5e f5e g5e",
            "e5e c#5e d5e a4e f5e g5e", "e5e c#5e a4e c#5e e5e g5e",
            "a5e f5e d6e a5e c6e d6e", "b5e a5e e5e c#5e g5e e5e",
            "f5e d5e a5e f5e d6e c6e", "e6e c6e g5e c6e b5e g5e",
            "a5e c6e f6e a6e e6e c6e", "d6e b5e c6e g5e b5e g5e",
            "a5e e5e g5e e5e c#5e e5e", "d5e a4e f4e e4e d4q"]
v1 = s.section("VAR1")
v1.voice("rh").bars(join(dyn(DIVISION, {0: "!p", 4: "cresc", 6: "!mp",
                                        8: "cresc", 12: "!mf", 14: "dim",
                                        15: "!p"})))
v1.voice("lh").bars(join(dyn([walk(i, mark="'") for i in range(16)],
                             {0: "!p", 8: "cresc", 12: "!mf", 14: "dim",
                              15: "!p"})))
s.tempo_change("VAR1", 1, 84)


# ── II: the theme as compound sixteenths, the bass in octaves ──
def compound(frag, h):
    """Each melody note on its beat, the chord tones under it filling
    the rest of its length in sixteenths."""
    out = []
    for p, d, _marks in notes(frag):
        x1 = below(p, h)
        x2 = below(x1, h)
        seq = [p, x1, x2, x1] * 3
        out += [nm(q) + "s" for q in seq[:round(DUR[d] / 0.25)]]
    return " ".join(out)


v2 = s.section("VAR2")
v2.voice("rh").bars(join(dyn([compound(m, h) for m, h in zip(THEME, HARM)],
                             {0: "!mf", 8: "cresc", 12: "!f", 13: "dim",
                              15: "!mf"})))
v2.voice("lh").bars(join(dyn([walk(i, octaves=True) for i in range(16)],
                             {0: "!mf", 8: "cresc", 12: "!f", 13: "dim",
                              15: "!mf"})))
v2.pedal(1)
s.tempo_change("VAR2", 1, 116)

# ── III: tempo di minuetto, the theme ornamented ──
MINUET = ["a4q +c#5 d5q. e5e", "f5q e5q.% d5e", "c#5q d5q. a4e",
          "b4q c5q.% g4e", "a4q +g5 f5q. e5e", "c5q g5q.% f5e",
          "e5q d5q. f5e", "e5h.%", "a5q +c#6 d6q. c6e", "b5q a5q.% g5e",
          "f5q a5q. d6e", "e6q c6q.% b5e", "a5q +g6 f6q. e6e",
          "d6q c6q.% b5e", "a5q g5q.% e5e", "d5h."]
v3 = s.section("VAR3")
v3.voice("rh").bars(join(dyn(MINUET, {0: "!mp", 8: "!mf", 12: "!f",
                                      14: "!mp"})))
v3.voice("lh").bars(join(dyn([walk(i, mark="_", line=WALK)
                              for i in range(16)],
                             {0: "!p", 8: "!mp", 12: "!mf", 14: "!p"})))
v3.rubato(0.02, phrase=2, shape="arch")
s.tempo_change("VAR3", 1, 104)
s.ritardando("VAR3", 16, 17, 88)

# ── IV: chorale, the pedal changed on every beat ──
def chorale(frags, harms, line):
    """Voice a melody, one fragment per 3/4 bar, as three-note chords:
    each note with two tones of its bar's chord within an octave below
    it. The inner voices are chosen over the whole passage by dynamic
    programming, so that no two voices, and no voice against the bass
    `line`, move in consecutive fifths or octaves, the inner voices move
    smoothly, and each chord keeps its third."""
    bass = [(3 * i + k, midi(n[0], n[1:-1], n[-1]))
            for i, bar in enumerate(line) for k, n in enumerate(bar.split())]

    def bass_at(t):
        return [p for u, p in bass if u <= t + 1e-9][-1]

    events, t = [], 0.0
    for i, (frag, h) in enumerate(zip(frags, harms)):
        t = 3.0 * i
        for p, d, marks in notes(frag):
            events.append((t, p, d, marks, h))
            t += DUR[d]
    states = []
    for t, p, _d, _m, h in events:
        tones = chord_pitches(h)
        pcs = {x % 12 for x in tones}
        third = (tones[1] if len(tones) > 1 else tones[0]) % 12
        floor = bass_at(t)
        cands = [x for x in range(p - 12, p) if x % 12 in pcs and x > floor]
        opts = []
        for x2 in cands:
            for x1 in cands:
                if x1 <= x2 or x1 - x2 < 2:
                    continue
                cost = 0.0
                if third not in {x2 % 12, x1 % 12, p % 12}:
                    cost += 3
                if len({x2 % 12, x1 % 12, p % 12}) < 3:
                    cost += 2
                opts.append(((x2, x1, p), cost))
        states.append(opts)

    def moves(prev, cur, b0, b1):
        cost = 0.0
        lines = list(zip(prev, cur)) + [(b0, b1)]
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                (u0, u1), (v0, v1) = lines[i], lines[j]
                if u0 != u1 and v0 != v1:
                    iv0, iv1 = (u0 - v0) % 12, (u1 - v1) % 12
                    if iv0 == iv1 and iv0 in (0, 7):
                        cost += 100
        return cost + 0.5 * (abs(prev[0] - cur[0]) + abs(prev[1] - cur[1]))

    best = [{v: (c, None) for v, c in states[0]}]
    for k in range(1, len(events)):
        t = events[k][0]
        b0, b1 = bass_at(t - 1e-6), bass_at(t)
        layer = {}
        for v, c in states[k]:
            layer[v] = min(((best[-1][u][0] + moves(u, v, b0, b1) + c, u)
                            for u in best[-1]), key=lambda x: x[0])
        best.append(layer)
    v = min(best[-1], key=lambda x: best[-1][x][0])
    chosen = []
    for k in range(len(events) - 1, -1, -1):
        chosen.append(v)
        v = best[k][v][1]
    chosen.reverse()
    bars_out = [[] for _ in frags]
    for (t, _p, d, marks, _h), v in zip(events, chosen):
        bars_out[int(t // 3)].append(
            "[" + " ".join(nm(x) for x in v) + "]" + d + marks)
    return [" ".join(b) for b in bars_out]


v4 = s.section("VAR4")
v4.voice("rh").bars(join(dyn(chorale(THEME, HARM, GROUND),
                             {0: "!pp", 4: "cresc", 6: "!p", 8: "cresc",
                              12: "!f", 13: "dim", 15: "!pp"})))
chorale_bass = [" ".join("ped " + b for b in walk_steps(i, octaves=True))
                for i in range(16)]
v4.voice("lh").bars(join(dyn(chorale_bass,
                             {0: "!pp", 4: "cresc", 6: "!p", 8: "cresc",
                              12: "!f", 13: "dim", 15: "!pp"})))
v4.rubato(0.05, phrase=4, shape="cradle")
s.tempo_change("VAR4", 1, 66)
s.ritardando("VAR4", 15, 17, 50)


# ── V: toccata, triplets traded between the hands ──
def on_beats(frag):
    """The melody note sounding on each beat of a 3/4 bar: the last
    note is heard on the third beat rather than after it."""
    ns = notes(frag)
    if len(ns) == 1:
        return [ns[0][0]] * 3
    return [ns[0][0], ns[1][0], ns[2][0]]


FIFTH = {"Dm": "[a1 a2]", "A7": "[e2 e3]", "A": "[e2 e3]", "C7": "[g1 g2]",
         "C": "[g1 g2]", "F": "[c2 c3]"}
toc_rh, toc_lh = [], []
for m, h in zip(THEME, HARM):
    beats = on_beats(m)
    toc_rh.append(" ".join(
        f"{{[{nm(below(p, h))} {nm(p)}] r [{nm(below(p, h))} {nm(p)}]}}q"
        for p in beats))
    toc_lh.append(" ".join(f"{{r {o} r}}q"
                           for o in (OCT[h], FIFTH[h], OCT[h])))
v5 = s.section("VAR5")
v5.voice("rh").bars(join(dyn(toc_rh, {0: "!mf", 8: "cresc", 12: "!f",
                                      15: "!mf"})))
v5.voice("lh").bars(join(dyn(toc_lh, {0: "!mf", 8: "cresc", 12: "!f",
                                      15: "!mf"})))
v5.pedal(1)
s.tempo_change("VAR5", 1, 144)

# ── VI: agitato, the theme in octaves over surging arpeggios ──
v6 = s.section("VAR6")
v6.voice("rh").bars(join(dyn(               # the second beat accented
    [voiced(m, lambda p, d: [p - 12, p]).replace("q. ", "q.> ")
     for m in THEME],
    {0: "!f", 8: "cresc", 12: "!ff", 13: "dim", 15: "!f"})))
surge = v6.voice("lh", vel=62)
surge.harmony(" ".join(HARM), octave=2, pattern="0 1 2 3 2 1", unit=0.5)
v6.pedal(1.5)
v6.rubato(0.03, phrase=2, shape="arch")
s.tempo_change("VAR6", 1, 126)
s.ritardando("VAR6", 16, 17, 104)

# ── VII: nocturne over quintuplets ──
v7 = s.section("VAR7")
v7.voice("rh").bars(join(dyn([m.replace("q.", "q._") for m in THEME],
                             {0: "!p", 8: "cresc", 12: "!mp", 13: "dim",
                              15: "!pp"})))
wave = v7.voice("wave", vel=30)
wave.harmony(" ".join(HARM), octave=3, pattern="0 1 2 3 2", unit=0.2)
v7.voice("bass").bars("!pp " + join(
    [OCT[h].split()[0].lstrip("[") + "h." for h in HARM]))
v7.pedal("bar")
v7.soft()
v7.rubato(0.06, phrase=2, shape="cradle")
s.tempo_change("VAR7", 1, 58)
s.ritardando("VAR7", 15, 17, 44)

# ── VIII: fugato in three voices ──
SUBJECT = ["dn4q an4q. gn4e", "fn4e gn4e an4e fn4e en4e dn4e",
           "en4e c#4e dn4e en4e fn4e gn4e", "an4e gn4e fn4e en4e dn4q"]
ANSWER = ["an4q en5q. dn5e", "cn5e dn5e en5e cn5e bn4e an4e",
          "bn4e g#4e an4e bn4e cn5e dn5e", "en5e dn5e cn5e bn4e an4q"]
COUNTER = ["cn4e dn4e en4e fn4e en4e fn4e", "en4q cn4q en4q",
           "en4q cn4q an3e bn3e", "cn4e bn3e an3e g#3e an3q"]
fg = s.section("FUGATO")
fg.voice("soprano").bars(join(
    ["rh."] * 4
    + dyn(ANSWER, {0: "!mf"})
    + ["!f dn5h en5q", "dn5h c#5q", "en5q dn5q bb4q", "an4q gn4q fn4q",
       "cresc fn5e gn5e an5e fn5e en5e dn5e", "en5e fn5e gn5e en5e dn5e cn5e",
       "dn5e en5e fn5e dn5e c#5e en5e", "!ff en5h.^"]))
fg.voice("alto").bars(join(
    dyn(SUBJECT, {0: "!mf"}) + COUNTER
    + ["!f " + transpose(COUNTER[0], 5, key="Dm")]
    + [transpose(c, 5, key="Dm") for c in COUNTER[1:]]
    + ["cresc an4e bb4e cn5e an4e gn4e fn4e", "gn4e an4e bb4e gn4e fn4e en4e",
       "fn4e gn4e an4e fn4e en4e gn4e", "!ff c#5h.^"]))
fg.voice("bass").bars(join(
    ["rh."] * 8
    + dyn([transpose(x, -12, key="Dm") for x in SUBJECT], {0: "!f"})
    + ["cresc dn3q cn3q gn2q", "cn3q bb2q fn2q", "bb2q dn3q an2q",
       "!ff [an1 an2]h.^"]))
s.tempo_change("FUGATO", 1, 100)
s.ritardando("FUGATO", 15, 16, 84)

# ── INTERMEZZO: a tempo rubato, turning to D-flat ──
im = s.section("INTERMEZZO", time="4/4")
im.voice("rh").bars(
    "!p an4q dn5q. en5e fn5q | en5q.% dn5e bb4h |"
    " cresc {bb4 cn5 db5 eb5 fn5 gb5 ab5}h !mf bb5h^ |"
    " dim ab5q. gb5e fn5q db5q | !p eb5q gb5q {fn5 eb5 db5 cn5 bb4}h |"
    " {ab5 gb5 fn5 eb5 db5 cn5 bb4 ab4 gb4 fn4 eb4 cn4}w |"
    " !pp [cn4 eb4 gb4 ab4]w&^ |")
im.voice("lh").bars(
    "!p [dn2 an2 fn3]w | [dn2 an2 fn3]h [bb1 fn2 dn3]h | [bb1 fn2 db3]w& |"
    " [gb1 db2 bb2]w | [eb2 bb2 gb3]h [ab1 eb2 gb2 cn3]h | [ab1 ab2]w |"
    " !pp [ab1 eb2]w^ |")
im.pedal("bar")
im.rubato(0.08, phrase=1, shape="cradle")
s.tempo_change("INTERMEZZO", 1, 54)
s.ritardando("INTERMEZZO", 6, 8, 40)

# ── IX: the theme inverted, in D-flat major ──
# Inverted about D and read in C major, the theme turns major; the
# second half is lifted an octave and closes on the tonic.
INV_A = ["g5q d5q. c5e", "b4q c5q. d5e", "e5q d5q. g5e", "f5q e5q. a5e",
         "g5q b4q. c5e", "e5q a4q. b4e", "c5q d5q. b4e", "c5h."]
INV_B = ["g5q d5q. e5e", "f5q g5q. a5e", "b5q g5q. d5e", "c5q e5q. f5e",
         "g5q b4q. c5e", "d5q e5q. f5e", "g5q a5q. b5e", "c6h."]
DB_A = ["Db", "Ab/C", "Fm7", "Gbmaj7", "Ab7", "Bbm", "Ab7", "Db"]
DB_B = ["Fm7", "Ebm7", "Ab", "Bbm7", "Fm", "Ebm7", "Ab9", "Db"]
db_a = [transpose(m, 1, key="C") for m in INV_A]
db_b = [transpose(m, 1, key="C") for m in INV_B]


def sung(frag, h):
    """A melody note with its chord tone under the stressed beat."""
    return voiced(frag, lambda p, d: [below(p, h), p] if d in ("q.", "h.")
                  else [p])


dfl = s.section("DFLAT", key="Db")
dfl.voice("rh").bars(join(
    dyn([sung(m, h) for m, h in zip(db_a, DB_A)], {0: "!p"})
    + dyn([sung(m, h) for m, h in zip(db_b, DB_B)],
          {0: "cresc", 4: "!mf", 5: "cresc"})
    + dyn([voiced(m, lambda p, d, h=h: [p, below(p + 12, h), p + 12])
           for m, h in zip(db_a, DB_A)],
          {0: "!ff", 4: "dim", 7: "!mp"})))
roll = dfl.voice("lh", vel=40)
roll.bars("!pp")
roll.harmony(" ".join(DB_A), octave=2, pattern="0 2 3 4 3 2", unit=1 / 3)
roll.bars("cresc")
roll.harmony(" ".join(DB_B), octave=2, pattern="0 2 3 4 3 2", unit=1 / 3)
roll.bars("!f")
roll.harmony(" ".join(DB_A), octave=2, pattern="0 1 2 3 4 5 4 3 2",
             unit=1 / 3)
roll.bars("!p")
dfl.pedal("bar")
dfl.rubato(0.05, phrase=2, shape="cradle")
s.tempo_change("DFLAT", 1, 63)
s.ritardando("DFLAT", 23, 25, 48)


# ── X: alla spagnola, sarabande bars and hemiolas ──
def spanish(i, frag, h):
    """A bar of the theme in thirds: even bars as the sarabande, the
    first beat strummed; odd bars as a hemiola of two dotted quarters."""
    ns = notes(frag)
    pair = [f"[{nm(below(p, h))} {nm(p)}]" for p, _d, _m in ns]
    if i % 2 == 0:
        return f"{pair[0]}q&> {pair[1]}q. {pair[2]}e'"
    return f"{pair[0]}q.&> {pair[1 if len(pair) > 1 else 0]}q.>"


def guitar(i, h):
    if i % 2 == 0:
        return f"{OCT[h]}q [{TENOR[h]}]q'& [{TENOR[h]}]q'&"
    return f"{OCT[h]}q. [{TENOR[h]}]q.'&"


sp = s.section("SPAGNOLA")
sp.voice("rh").bars(join(dyn([spanish(i, m, h)
                              for i, (m, h) in enumerate(zip(THEME, HARM))],
                             {0: "!f", 8: "!mf", 10: "cresc", 12: "!ff"})))
sp.voice("lh").bars(join(dyn([guitar(i, h) for i, h in enumerate(HARM)],
                             {0: "!f", 8: "!mf", 10: "cresc", 12: "!ff"})))
s.tempo_change("SPAGNOLA", 1, 138)

# ── XI: climax, the theme in the bass under hammered triplets ──
UPPER = {"Dm": "a4 d5 f5 a5", "A7": "a4 c#5 e5 g5", "A": "a4 c#5 e5 a5",
         "C7": "g4 bb4 c5 e5", "C": "g4 c5 e5 g5", "F": "a4 c5 f5 a5"}
rise = " ".join(f"[{nm(p)} {nm(p + 12)}]s" for p in range(69, 81))
fall = " ".join(f"[{nm(p - 12)} {nm(p)}]s" for p in range(45, 33, -1))
A7_TOP = "[a4 c#5 e5 g5 a5]"
cl = s.section("CLIMAX")
cl.voice("rh").bars(join(
    dyn([" ".join(f"{{[{UPPER[h]}] [{UPPER[h]}] [{UPPER[h]}]}}q"
                  for _ in range(3)) for h in HARM],
        {0: "!ff", 8: "cresc", 12: "!fff"})
    + ["cresc " + rise, f"!fff {A7_TOP}q> {A7_TOP}q> {A7_TOP}q>",
       "[c#5 e5 g5 a5 c#6]h.&^", "rh.^"]))
cl.voice("lh").bars(join(
    dyn([voiced(m, lambda p, d: [p - 36, p - 24]).replace("q. ", "q.> ")
         for m in THEME], {0: "!ff", 8: "cresc", 12: "!fff"})
    + ["cresc " + fall, "!fff [a0 a1]q> [a0 a1]q> [a0 a1]q>",
       "[a0 a1 e2 a2]h.&^", "rh.^"]))
cl.pedal(1)
s.tempo_change("CLIMAX", 1, 120)
s.ritardando("CLIMAX", 17, 19, 96)

# ── CODA: the theme sinks away under distant bells ──
cd = s.section("CODA")
cd.voice("melody").bars(
    "!pp a4q d5q. e5e | f5q e5q. d5e | c#5q d5q. a4e | b4q a4q. g4e |"
    " f4q e4q. d4e | c#4h. | d4h. | rh. |")
cd.voice("bells", vel=26).bars(
    "!pp d6h. | a5h. | d6h. | b5h. | a5h. | e5h. | f5h. |"
    " !ppp [a3 d4 f4 a4 d5]h.&^~ |")
cd.voice("lh").bars(
    "!pp [d2 a2 f3]h. | [d2 a2 f3]h. | [d2 a2 f3]h. | [d2 g2 b2]h. |"
    " [d2 a2 f3]h. | [a1 e2 g2]h. | [d1 d2]h. | !ppp [d1 a1 d2]h.^~ |")
cd.pedal("bar")
cd.soft()
s.tempo_change("CODA", 1, 56)
s.ritardando("CODA", 5, 9, 38)

s.arrange("THEME VAR1 VAR2 VAR3 VAR4 VAR5 VAR6 VAR7 FUGATO INTERMEZZO"
          " DFLAT SPAGNOLA CLIMAX CODA")
s.describe()
s.lint(mode="homophonic")
out = s.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "rachmaninoff_folia_variations.mid"))
print("wrote", out)
if "--play" in sys.argv:
    s.play()
