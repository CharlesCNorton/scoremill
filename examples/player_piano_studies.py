#!/usr/bin/env python3
"""Five Studies for Player Piano.
After Conlon Nancarrow, who punched his rolls by hand because no
pianist could play them. These take the player-piano ethos to its
limit: music conceived for a machine that does not tire, cannot miss,
and has no hands to run out of. Each study is generated and written
straight into the voices through scoremill's raw Note API, the layer
below the notation, because music of this density is composed by
process, not typed.

  1. Tempo Canon      one subject, four voices, four simultaneous
                      tempos in the ratio 6:4:3:2, drifting and lapping.
  2. Prime Ostinato   seven ostinati of coprime length running at once;
                      the composite does not repeat for thousands of bars.
  3. Acceleration     one line accelerating and one decelerating across
                      the same span, crossing in the middle, over a pulse.
  4. Cascades         full-keyboard sweeps in three staggered voices,
                      faster than any run a hand could take.
  5. Tutti            everything at once, closing on an 88-key avalanche
                      and a chord spanning most of the keyboard.

    python player_piano_studies.py            # summarize all five
    python player_piano_studies.py 3 --play   # perform study 3
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoremill import Song, Note


def note(pitches, beats, vel, gate=0.9):
    if not isinstance(pitches, (list, tuple)):
        pitches = [pitches]
    keep = [max(21, min(108, p)) for p in pitches]
    return Note(keep, beats, max(1, min(127, vel)), gate)


def rest(beats):
    return Note([], beats, 0)


def pad(voice, total):
    """Extend a voice with a trailing rest so every voice in a section
    ends at exactly the same beat (scoremill requires it)."""
    d = round(total - voice.total_beats(), 6)
    if d > 1e-9:
        voice.notes.append(rest(d))


def grid(voice, pitch_of, step, total, vel_of):
    """Fill `total` beats with equal `step` notes; pitch_of(i) and
    vel_of(i) supply each note. Count is floored so the voice never
    overshoots, then padded to land exactly on `total`."""
    count = int(total / step + 1e-9)
    for i in range(count):
        voice.notes.append(note(pitch_of(i), step, vel_of(i)))
    pad(voice, total)


# ── 1. TEMPO CANON ──────────────────────────────────────────
def tempo_canon():
    s = Song(tempo=120, time="48/4", key="C", humanize=0, expressive=False)
    OFF = [0, 7, 12, 7, 4, 0, 4, 7, 3, 0, -5]
    DUR = [1, .5, .5, 1, 1, .5, .5, 1, .5, .5, 1]     # sums to 8 beats
    sec = s.section("Canon")
    # (root, tempo scale, repetitions, velocity); each fills 48 beats.
    for root, scale, reps, vel in [(72, 1.0, 6, 68), (60, 1.5, 4, 62),
                                   (48, 2.0, 3, 56), (36, 3.0, 2, 50)]:
        v = sec.voice(f"v{root}")
        for _ in range(reps):
            for off, d in zip(OFF, DUR):
                v.notes.append(note(root + off, d * scale, vel))
        pad(v, 48.0)
    return s.arrange("Canon")


# ── 2. PRIME OSTINATO ───────────────────────────────────────
def prime_ostinato():
    s = Song(tempo=132, time="64/4", key="C", humanize=0, expressive=False)
    sec = s.section("Ostinato")
    T, STEP = 64.0, 0.25
    PENTA = [0, 2, 4, 7, 9]
    # (period, base pitch, index stride, velocity)
    for P, base, k, vel in [(3, 36, 3, 54), (5, 48, 2, 52), (7, 55, 3, 50),
                            (11, 64, 1, 48), (13, 72, 4, 46),
                            (17, 79, 2, 44), (19, 86, 3, 42)]:
        pat = [base + PENTA[(i * k) % 5] + 12 * (((i * k) // 5) % 2)
               for i in range(P)]
        v = sec.voice(f"p{P}")
        grid(v, lambda i, pat=pat, P=P: pat[i % P], STEP, T,
             lambda i, vel=vel: vel)
    return s.arrange("Ostinato")


# ── 3. ACCELERATION ─────────────────────────────────────────
def acceleration():
    s = Song(tempo=120, time="20/4", key="C", humanize=0, expressive=False)
    sec = s.section("Accel")
    T, N, r = 20.0, 80, 0.94
    w = [r ** k for k in range(N)]
    W = sum(w)
    up = [T * x / W for x in w]            # long to short: accelerating
    down = up[::-1]                        # short to long: decelerating
    va = sec.voice("accel")
    p = 48
    for d in up:
        va.notes.append(note(p, d, 62))
        p = 48 + (p - 47) % 48             # rising chromatic wrap
    pad(va, T)
    vb = sec.voice("decel")
    p = 84
    for d in down:
        vb.notes.append(note(p, d, 56))
        p = 84 - (84 - p + 1) % 48         # falling chromatic wrap
    pad(vb, T)
    vc = sec.voice("pulse")               # a steady low heartbeat
    grid(vc, lambda i: 33 if i % 2 == 0 else 28, 1.0, T, lambda i: 46)
    return s.arrange("Accel")


# ── 4. CASCADES ─────────────────────────────────────────────
def cascades():
    s = Song(tempo=120, time="32/4", key="C", humanize=0, expressive=False)
    sec = s.section("Cascades")
    sec.pedal("bar")                       # one long resonant wash
    T = 32.0

    def sweep(vname, delay, lo, hi, step, dirn, vel):
        v = sec.voice(vname)
        if delay:
            v.notes.append(rest(delay))
        span = list(range(hi, lo - 1, -2) if dirn < 0
                    else range(lo, hi + 1, 2))
        t = delay
        i = 0
        while t < T - 1e-9:
            v.notes.append(note(span[i % len(span)], step, vel))
            i += 1
            t += step
        pad(v, T)

    sweep("c1", 0.0, 24, 104, 1 / 12, -1, 56)      # whole-tone waterfall down
    sweep("c2", 0.5, 21, 101, 1 / 12, +1, 52)      # a rising sheet, offset
    sweep("c3", 1.0, 28, 108, 1 / 16, -1, 48)      # faster, higher, down
    return s.arrange("Cascades")


# ── 5. TUTTI ────────────────────────────────────────────────
def tutti():
    s = Song(tempo=126, time="24/4", key="C", humanize=0, expressive=False)
    main = s.section("Tutti")
    T = 24.0
    OB = [36, 31, 36, 43, 36, 31, 38, 43]
    grid(main.voice("bass"), lambda i: OB[i % 8], 0.25, T, lambda i: 64)
    AR = [60, 64, 67, 72, 76, 72, 67, 64]
    grid(main.voice("mid"), lambda i: AR[i % 8], 0.125, T, lambda i: 52)
    grid(main.voice("top"), lambda i: 72 + 2 * (i % 18), 1 / 12, T,
         lambda i: 48)
    vc = main.voice("stab")                # a fat 12-note stab every 2 beats
    stab = [24 + i * 7 for i in range(12)]
    t = 0.0
    while t < T - 1e-9:
        vc.notes.append(note(stab, 0.25, 72))
        vc.notes.append(rest(1.75))
        t += 2.0
    pad(vc, T)

    coda = s.section("Coda")
    coda.pedal("bar")
    va = coda.voice("avalanche")           # every key, bottom to top
    for p in range(21, 109):
        va.notes.append(note(p, 1 / 16, 38 + (p - 21) // 4))
    mega = list(range(24, 104, 4))         # a 20-note keyboard-wide chord
    va.notes.append(note(mega, 4.0, 92, gate=1.4))
    return s.arrange("Tutti Coda")


BUILD = {1: tempo_canon, 2: prime_ostinato, 3: acceleration,
         4: cascades, 5: tutti}
TITLE = {1: "Tempo Canon", 2: "Prime Ostinato", 3: "Acceleration",
         4: "Cascades", 5: "Tutti"}


def main():
    args = sys.argv[1:]
    play = "--play" in args
    which = [int(a) for a in args if a.isdigit()] or [1, 2, 3, 4, 5]
    here = os.path.dirname(os.path.abspath(__file__))
    for n_study in which:
        song = BUILD[n_study]()
        notes = sum(1 for sec in song.sections.values()
                    for v in sec.voices for nn in v.notes if nn.pitches)
        print(f"Study {n_study} - {TITLE[n_study]}: "
              f"{notes} notes, {song._duration_s():.0f}s")
        song.save(os.path.join(here, f"player_piano_study_{n_study}.mid"))
        if play:
            song.play()


if __name__ == "__main__":
    main()
