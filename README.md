# scoremill

Text-notation MIDI composition for language-model agents.

## The bet

Machine music today mostly means generation models: sample the weights,
keep the audio. What comes out can be striking, but it is a performance
without a score. There is nothing to read, nothing to revise, no theme
to develop, and no way for the author to verify its own work short of
listening, which an agent cannot do.

Scoremill is the other bet: that an agent which can reason should
compose the way literate musicians always have, in notation. A piece
here is a short text. Development is a function applied to a theme.
Correctness is checked before a note sounds, and the score can be
diffed, transposed, inverted, linted, and argued about, because it is
symbolic all the way down. As agents grow more capable this bet
compounds, since a model that writes scores can explain them, refactor
them, and build a style deliberately rather than sampling one. We
think this is the winning branch, and as far as we know scoremill is
the first library built for it.

The design grew from one observation: an agent composing in text
cannot hear its mistakes, so the notation layer must catch them
instead. Every bar is validated at parse time, errors come with
corrective hints, a counterpoint linter flags collisions and
parallels, and `report()` returns a structured summary the author can
assert on. The feedback loop stands in for ears. It was written by an
agent, for agents, composing on a real piano, and its details come
from the mistakes actually made along the way. Humans are welcome too.

Use it through the notation, or raw: `Song`, `Voice`, the transforms,
and the renderer are ordinary Python, importable a la carte, and the
tick-level event stream is available to any agent that prefers to
work below the notation.

## The demo score

`examples/saltarello_alla_chico.py` is the house demonstration: a 6/8
novelty saltarello with a staccato jump tune over an oom-pah left
hand, grace-note pickups, pistol-finger accents, a cadential trill, an
echo strain built with `variant()`, a coda that turns to A major by
switching the section key signature, and an accelerando through a
sixteenth run to one last plink at the top of the keyboard.

```
python examples/saltarello_alla_chico.py          # renders the .mid
python examples/saltarello_alla_chico.py --play   # performs it
```

## Install

```
pip install mido            # rendering to .mid files
pip install python-rtmidi   # optional: real-time playback ports
```

Then copy `scoremill.py` into your project, or `pip install -e .` from
a clone.

## Sixty seconds

```python
from scoremill import Song, shift

s = Song(tempo=96, time="4/4", key="Am", humanize=1)

MOTIF = "a4e c5e e5q d5e c5e"               # three beats of material
A = s.section("A")
A.voice("rh", vel=52).bars(
    f"!mp {MOTIF} b4q | {shift(MOTIF, -1)} a4q |"
    "  e5q {d5 c5 b4}q a4h |"               # triplet on beat two
    "  [a3 c4 e4]w^& |")                    # rolled final chord, fermata
A.voice("lh", vel=36).harmony(
    "Am G Am E7", style="broken", voicing="smooth")
A.pedal("bar")
s.ritardando("A", 3, 4, 70)
s.arrange("A")

s.describe()                # printed summary
s.lint()                    # counterpoint findings
s.save("evening.mid")       # render
s.play()                    # or perform on the first MIDI output
```

If a bar does not add up, the parse fails immediately and says so:

```
voice 'A.rh' bar 2: has 3.0 beats, expected 4.0 — short by 1.0 beats (a 'q').
    bar was: d4e b4e c5q g4q
```

## Notation

| Element | Syntax | Notes |
|---|---|---|
| Pitch | `c d e f g a b` + `# b n` + octave | octave is sticky per voice; key signature applies (`key="F"` makes `b` mean B-flat, `bn` natural); minor keys (`Am`, `Dm`, ...) supported |
| Duration | trailing `w h q e s t`, optional `.` | sticky; `r` = rest |
| Chord | `[c4 e g]h` | shared duration |
| Tuplet | `{c4 d4 e4}q`, `{[c4 e4] d4}q` | members divide the span equally; a member may be a chord |
| Grace | `+d5` | sounds just before the next note; stackable |
| Tie | `c5h~` | the next note must repeat the pitch (validated); a tie on a voice's last note is laissez vibrer |
| Marks | `>` accent · `'` staccato · `_` legato · `^` fermata · `&` roll · `%` trill | after the duration; fermata length and trill rate are configurable on `Song` |
| Dynamics | `!ppp !pp !p !mp !mf !f !ff !fff`, `cresc`, `dim` | sticky; cresc/dim interpolate to the next mark, which must exist (validated) |
| Barline | `\|` | asserts the bar is exactly full |

## Motif transforms

Development as string-to-string functions. Write a subject once and
derive the rest:

```python
shift(frag, 2)              # diatonic sequence up two steps
invert(frag, axis="g4")     # mirror about an axis pitch
retro(frag)                 # retrograde
stretch(frag, 2)            # augmentation (0.5 for diminution)
rebar(frag, 3)              # re-insert barlines every 3 beats
```

Explicit alterations travel with their scale degree under `shift` and
are mirrored under `invert` (a raised degree inverts to a lowered
one). `retro` insists the fragment contain no barlines, dynamics, or
ties; apply those around the result. `stretch` changes durations and
therefore the barring, so pair it with `rebar`, which re-inserts
barlines at a chosen bar length and errors if a note would straddle
one.

## Harmony

```python
voice.harmony("C Am7 F G7", style="stride", voicing="smooth",
              avoid=melody)
```

Twenty-six chord qualities (`m 7 maj7 m7 6 m6 dim dim7 m7b5 aug sus2
sus4 9 maj9 m9 add9 mmaj7 m11 7sus4 9sus4 7b5 7#5 7b9 7#9 11 13`),
slash basses (`C/G`), and eight accompaniment styles (`block root
fifth waltz alberti arp broken stride`; waltz, stride, and broken fill
fractional meters). `voicing="smooth"` chooses inversions that
minimize movement between chords. `harmony()` takes its own `octave`
argument for the register of the chord roots, independent of the
octave the voice uses for melodic input.

`avoid=<voice>` makes the accompaniment melody-aware: chord tones that
would double the named voice's pitch classes on a shared onset are
dropped, and single figure tones that would collide at the exact
unison move an octave away. When the song declares a pickup and the
accompaniment voice is still empty, `harmony()` inserts the pickup
rest itself.

## Expression

```python
Song(swing=0.62, swing_unit="sixteenth", humanize=2, expressive=True,
     fermata=1.6, trill_rate=0.125)
section.rubato(0.05, phrase=2, shape="arch")   # or "cradle"
section.pedal("bar")                # "half", or a number of beats
section.soft()                      # una corda for the section
s.tempo_change("A", bar=5, bpm=80)  # step change
s.ritardando("A", 7, 8, 60)         # linear ramp; a faster target
                                    # produces an accelerando
```

`expressive` adds downbeat lean, melodic-contour shading, and top-note
voicing inside chords; `humanize` adds slight timing and velocity
variation. `swing_unit` swings eighths or sixteenths; `fermata` sets
how far a `^` note overshoots its written length; `trill_rate` sets a
`%` trill's alternation speed. Rubato is an `"arch"` that presses
forward and relaxes, or a `"cradle"` that broadens mid-phrase.

## Analysis

```python
s.lint()      # collisions and parallels, located by bar and beat
s.report()    # dict: sections, voices, ranges, density, duration, lint
```

`lint()` reports two things, each located by bar and beat: collisions,
where two voices sound the same pitch at once, whether struck together
or struck against a held note; and consecutive parallel fifths or
octaves, checked on both the top and the bottom line of each voice
pair. `report()` exists so an agent can check its own work
programmatically, and its duration integrates the full tempo map:

```python
assert s.report()["duration_s"] < 180
assert not s.report()["lint"]
```

The linter is advisory. Styles that double the tune and the
accompaniment on strong beats will trip the parallel checks on
purpose; read the findings, keep the ones that are idiom, fix the
ones that are accidents. When a texture doubles by design, pass
`lint(mode="homophonic")` to keep only the collisions.

## Raw access

Notation is the front door, not the only one. `song.events()` returns
the fully expressive event stream as sorted `(tick, kind, channel, a,
b)` tuples at 480 ticks per beat, exactly what `save()` and `play()`
render, for agents that prefer to work below the notation:

```python
for tick, kind, ch, a, b in song.events():
    ...            # kind in {"on", "off", "cc64", "cc67", "tempo"}
```

`Song`, `Voice`, the transforms, and the renderer are ordinary Python,
importable a la carte; a `Voice`'s `notes` list accepts hand-built
`Note` objects, which bypass notation validation.

## Playback

`play()` streams in real time through [mido](https://mido.readthedocs.io)
(requires `python-rtmidi`). It picks the first hardware output, or
match one by substring: `s.play(port="FluidSynth")`. `play(count_in=4)`
taps four beats before the music; `play(progress=fn)` calls `fn` with
each message as it goes out. Playback releases all notes and both
pedals on exit, so an interrupt leaves nothing hanging. Without
hardware, render with `save()` and use any soft synth, for example:

```
fluidsynth -a pulseaudio soundfont.sf2 piece.mid
```

A pitched-instrument range guard rejects notes a piano cannot play;
widen it for synths with `Song(pitch_range=(0, 127))`.

## Examples

| File | Demonstrates |
|---|---|
| `examples/saltarello_alla_chico.py` | the demo score: variants, per-section keys, grace notes, trill, accelerando |
| `examples/minuet_small_computer.py` | sections, waltz harmony, arrangement |
| `examples/blues_416_megabytes.py` | swing, grace notes, stride, rubato |
| `examples/invention_two_processes.py` | motif transforms, two-voice counterpoint, lint |
| `examples/orrery.py` | process music: prime-period orbits, overtone pitches |

Running an example writes its `.mid` next to it; add `--play` to
perform it on a connected MIDI output.

## License

MIT.
