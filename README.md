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
pip install scoremill           # library (pulls mido)
pip install scoremill[play]     # + python-rtmidi for real-time ports
```

Or copy `scoremill.py` into your project — it is a single file — or
`pip install -e .` from a clone. The package installs three modules:
`scoremill`, the library; `jukebox`, the player (`python -m jukebox`);
and `mcp_server`, the MCP server (`python -m mcp_server`).

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
| Duration | trailing `w h q e s t x` (whole to sixty-fourth), up to two dots (`q.`, `q..`) | sticky; `r` = rest |
| Repeat | `c4e*4`, `(c4e d4e)*3`, `(c4w \|)*8` | writes a token or a group out N times; a group may hold barlines |
| Chord | `[c4 e g]h` | shared duration |
| Tuplet | `{c4 d4 e4}q`, `{[c4 e4] d4}q`, `{c4 {d4 e4 f4} g4}q` | members divide the span equally; a member may be a chord, or a tuplet of its own that divides the member's share |
| Grace | `+d5` | sounds just before the next note; stackable |
| Tie | `c5h~` | the next note must repeat the pitch (validated); a tie on a voice's last note is laissez vibrer |
| Marks | `>` accent · `'` staccato · `_` legato · `^` fermata · `&` roll · `%` trill | after the duration; a fermata holds the moment, stretching time by `Song(fermata=)` (on a rest, `rh^`, it is a general pause); trill rate is configurable on `Song` |
| Pedal | `ped`, `lift` | `ped` presses the sustain pedal at the next note, or changes it there; `lift` releases it; a section ends lifted |
| Dynamics | `!ppp !pp !p !mp !mf !f !ff !fff`, `cresc`, `dim` | sticky; cresc/dim interpolate to the next mark, which must exist (validated), and keep accents |
| Barline | `\|` | asserts the bar is exactly full; `Song(pickup=N)` allows a short first bar, and bars then count from the first downbeat |
| Meter | `M:3/4` | opens a bar and sets the meter from there on for every voice of the section; `section.time_change(9, "3/4")` declares the same change, and a section may take its own `time=`; bar checks, bar numbers, pedaling, `harmony(slots="bar")`, and the engraving follow the meters |
| Onset | `c5e@3` | after `voice.absolute_onsets()`, starts the note at beat 3 of the voice; a gap fills with a rest, the marks and graces written before the note stay with it, and an onset that earlier material already passed is an error |
| Drums | `bde hh sn hh`, `[bd hh]q` | in a `section.drums()` voice (General MIDI channel 10): drum names in place of pitches, with durations, stacks, and `>` accents |

## Motif transforms

Development as string-to-string functions. Write a subject once and
derive the rest:

```python
shift(frag, 2)              # diatonic sequence up two steps
invert(frag, axis="g4")     # mirror about an axis pitch
retro(frag)                 # retrograde
stretch(frag, 2)            # augmentation (0.5 for diminution)
rebar(frag, 3)              # re-insert barlines every 3 beats
transpose(frag, 3)          # chromatic: up a minor third
double(frag, -7)            # in octaves (the octave below added)
map_notes(frag, fn)         # each note through a function of your own
```

Explicit alterations travel with their scale degree under `shift` and
are mirrored under `invert` (a raised degree inverts to a lowered
one). `retro` insists the fragment contain no barlines, dynamics, or
ties; apply those around the result. A grace note travels with the
note it ornaments, tuplet members reverse within their tuplet, and
sticky octaves and durations are written out first so the reversal
cannot change what a token means. `stretch` changes durations and
therefore the barring, so pair it with `rebar`, which re-inserts
barlines at a chosen bar length and errors if a note would straddle
one.

`transpose(frag, semitones, key="C")` is the chromatic counterpart of
`shift`. It reads the fragment in `key` and spells each result by
interval, so up a minor third from B is D rather than C double-sharp,
with explicit accidentals that read the same under any signature. To
move a finished piece to another key, `song.transpose(semitones)`
shifts every entered note in place and relabels the keys, raising if a
note would leave the instrument range.

`double(frag, degrees)` thickens a line the way a pianist does:
`double(tune, -7)` plays it in octaves, `double(tune, 7)` adds the
octave above, and `double(tune, -2)` adds a third below. An octave
keeps each note's accidental, so it is exact; a third or a sixth takes
the key signature, as a hand playing in thirds does. Chords double
every member and tuplet members become chords.

`map_notes(frag, fn, key="C")` is the general form of `double()`. It
hands `fn` every note of the fragment, tuplet members included, as a
`Mapped` with the note's MIDI `pitch`, its length in `beats`, its onset
`at` in beats from the fragment's start, and its `bar`, counted from 0.
Whatever `fn` returns is written back: a pitch, a list of pitches as a
chord, an empty list for a rest, or `None` to keep the note. Rests,
chords, grace notes, marks, dynamics, and onset anchors pass through,
and every pitch comes back with its octave and accidental written out.
With `chord_tone_below(pitch, symbol)`, the highest tone of a chord at
least a minor third under a pitch, it voices a tune over a progression
in one call:

```python
PROG = ["F", "C"]
map_notes("a4q a4e b4e c5q a4q | g4q e4q c4h |",
          lambda n: [chord_tone_below(n.pitch, PROG[n.bar]), n.pitch],
          key="F")
# '[fn4 an4]q [fn4 an4]e [fn4 bb4]e [an4 cn5]q [fn4 an4]q |
#  [en4 gn4]q [cn4 en4]q [gn3 cn4]h |'
```

`same_shape(a, b, key="C")` says whether two fragments carry the same
rhythm and the same intervals, one an exact chromatic transposition of
the other, compared on the top note of each chord. Rhythm here means
where the notes are struck, so a staccato restatement still matches.
It checks that a motif was moved and not altered: `transpose(m, 5)`
passes, while `shift(m, 1)` moves the tune through the scale, changes
its intervals, and fails.

## Harmony

```python
voice.harmony("C Am7 F G7", style="stride", voicing="smooth",
              avoid=melody)
```

Twenty-six chord qualities (`m 7 maj7 m7 6 m6 dim dim7 m7b5 aug sus2
sus4 9 maj9 m9 add9 mmaj7 m11 7sus4 9sus4 7b5 7#5 7b9 7#9 11 13`),
slash basses (`C/G`), and eight accompaniment styles (`block root
fifth waltz alberti arp broken stride`; waltz, stride, and broken fill
fractional meters). `voicing=` chooses how each chord is spelled:
`plain` (close position), `smooth` (inversions that minimize movement
between chords), `shell` (root, third, and seventh), `rootless` (drop
the root for a comping color), or `drop2` (lower the second voice from
the top an octave, a wider open spread). A slash bass is never
disturbed. `harmony()` takes its own `octave` argument for the
register of the chord roots, independent of the octave the voice uses
for melodic input.

Any figure the styles do not cover can be written as a `pattern`:
indices into the chord's tone ladder, which is its tones stacked up by
octaves with a slash bass at index 0, stepped `unit` beats at a time
and repeated to fill each slot. `"0+4"` strikes two ladder tones at
once and `"r"` rests. A step may carry its own length after a colon,
so a pattern can have a rhythm; steps without one take `unit`, and the
steps must fill each slot exactly. A rolling Rachmaninoff left hand in
triplets, a Horowitz piccolo obbligato, or a habanera bass is one line:

```python
lh.harmony("Bbm Bbm/A Gb F7", slots="half", octave=2,
           pattern="0 2 3 4 3 2", unit=1/3)
piccolo.harmony("Ab Eb7*2 Ab", octave=5, pattern="3 4 5 6 5 4 3 4",
                unit=0.25)
lh.harmony("Dm A7 Dm A7", octave=2, pattern="0:e. 4:s 2+3:e 2+3:e")
```

Chord symbols repeat with `*` (`"Am*4"`). `slots="half"` places two
symbols in a bar, and a number places one per that many beats, so
`slots=1` splits a 3/4 bar one beat plus two with `"Dm A7 ."`.
`transpose_chords("C G7/B Am", 1)` moves a progression, spelled for
its new key: `"Db Ab7/C Bbm"`.

`harmonize(melody, symbols, key=, voices=3, bass=)` voices the melody
itself as chords, string to string: each note becomes the top of a
chord of `voices` notes drawn from the symbol under it. The added notes
are chosen across the whole passage by dynamic programming, so no two
voices, and no voice against the given bass line, move in consecutive
fifths or octaves, the inner voices move as little as they can, and
each chord keeps its third; a tied note keeps its chord, and rests,
graces, trills, and marks pass through. It is the counterpart of
`lint()`: where the linter finds parallels in chords stacked by hand,
`harmonize` does not write them.

```python
rh.bars(harmonize(theme, "Dm A7 Dm C7 F C Dm A", key="Dm", bass=ground))
```

`avoid=<voice>` makes the accompaniment melody-aware: chord tones that
would double the named voice's pitch classes on a shared onset are
dropped, and single figure tones that would collide at the exact
unison move an octave away. When the song declares a pickup and the
accompaniment voice is still empty, `harmony()` inserts the pickup
rest itself; the rest gives way when the voices written by hand open
on a downbeat, whichever is written first.

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
how much longer the music takes under a `^` (the tempo is divided by
it there, for every voice); `trill_rate` sets a `%` trill's
alternation speed. Rubato is an `"arch"` that presses forward and
relaxes, or a `"cradle"` that broadens mid-phrase. Hairpins follow
time rather than the note count, so a trill inside one takes only its
share of the swell.

For pedaling that follows the harmony rather than the barline, write
it into a voice: `ped` presses (or changes) the pedal at the next note
and `lift` releases it. `section.swing(0.66)` gives one section its own
swing, so a straight verse can lead into a swung chorus, and
`Song(dynamics={"p": 45, "f": 80})` retunes the velocity of any
dynamic mark to suit an instrument's touch.

Tempo changes, ramps, and rubato belong to their section, and every
section begins at the song tempo. In a section that opens with a
pickup, bar numbers, pedal changes, swing, and the downbeat lean all
count from the first downbeat, as `lint()` does.

## Analysis

```python
s.lint()      # collisions and parallels, located by bar and beat
s.rubs()      # seconds and sevenths that ring together, pedal included
s.report()    # dict: sections, voices, density, duration, lint, rubs
s.chords()    # the harmony that sounds, beat by beat
s.find(motif) # every exact statement of a motif, at any transposition
```

`lint()` reports two things, each located by bar and beat: collisions,
where two voices sound the same pitch at once, whether struck together
or struck against a held note; and consecutive parallel fifths or
octaves, checked on both the top and the bottom line of each voice
pair. `lint(mode="strict")` adds voice crossings, unresolved leading
tones, unprepared dissonances struck on a beat, extreme or very wide
tessitura, and unrolled chords wider than a tenth, which one hand
cannot reach; these fire on free counterpoint by design.
`lint(only="Fugato")` checks one section, so a fugato can be held to
full counterpoint inside a piece linted as homophonic.

`chords(per="beat")` names the chord that sounds in each beat (or half
bar, or bar), weighing every pitched voice's notes by how long they
sound and writing a slash bass when the lowest note is not the root.
Runs of one chord merge. It is the closest thing to ears: compare the
progression you meant with the one you wrote.

```python
>>> s.chords(per="bar")
[{'section': 'A', 'at': 'bar 1 beat 1', 'beats': 4.0, 'chord': 'C'},
 {'section': 'A', 'at': 'bar 2 beat 1', 'beats': 4.0, 'chord': 'G7'}]
```

`rubs()` reports the dissonance a listener hears, which the
counterpoint checks do not look for: notes of two voices a minor
second, a major seventh, or a minor ninth apart that ring together for
at least `min_beats` (half a beat by default). A note rings until its
release, or, while the sustain pedal is down, until the pedal next
changes, following the section's `pedal()` setting and its `ped` and
`lift` marks. A passing tone the pedal catches under a chord is found
where a dry performance would let it go, and a grace note counts,
since under the pedal it rings on. Each finding names the voices, the
notes as written, the interval, and how long they sound together:

```python
A.voice("rh").bars("e5e f5e g5q c6h | c6w |")
A.voice("lh").bars("[c4 e4 g4]w | [c4 e4 g4]w |")
A.pedal("bar")
s.rubs()
# [A] rub lh/rh at bar 1 beat 1.5: en4 against fn5 (minor ninth),
#     ringing together 3.5 beats
```

Without the pedal the same bars report nothing, since the F sounds for
less than half a beat. `rubs(only="A")` checks one section.

`find(motif)` lists every place a motif sounds with its rhythm and
every interval intact, at any exact transposition, compared on each
voice's top notes with tied notes joined. Rhythm is where the notes
are struck, so a staccato statement matches the motif as written. A
statement altered in any interval or onset does not match, so after
writing variations the finds show whether the theme survived them:

```python
>>> A.voice("rh").bars("c5e d5e e5q g5h | f5e' g5e' a5q c6h |"
...                    " c5e d5e e5q f5h | c5w |")
>>> A.voice("lh").bars("c3e d3e e3q g3h | f2w | g2w | c3w |")
>>> s.find("c5e d5e e5q g5h")
[{'section': 'A', 'voice': 'rh', 'at': 'bar 1 beat 1', 'semitones': 0},
 {'section': 'A', 'voice': 'rh', 'at': 'bar 2 beat 1', 'semitones': 5},
 {'section': 'A', 'voice': 'lh', 'at': 'bar 1 beat 1', 'semitones': -24}]
```

The third bar changes the last interval and is not reported.

`report()`
exists so an agent can check its own work programmatically. Each voice
in it carries a pitch-class histogram, its out-of-key rate, the
distribution of melodic intervals, bar-to-bar self-similarity, and a
grace-note count, and its duration integrates the full tempo map. It
also carries the lint findings and the rubs:

```python
assert s.report()["duration_s"] < 180
assert not s.report()["lint"]
assert not s.report()["rubs"]
```

The linter is advisory. Styles that double the tune and the
accompaniment on strong beats will trip the parallel checks on
purpose; read the findings, keep the ones that are idiom, fix the
ones that are accidents. When a texture doubles by design, pass
`lint(mode="homophonic")` to keep only the collisions.

## Reading MIDI

`Song.from_midi(path)` reads a Standard MIDI File into a Song, so music
scoremill did not write can be examined with the same tools, and
transposed, engraved, or rendered again:

```python
s = Song.from_midi("examples/saltarello_alla_chico.mid")
s.describe()                                # 40 bars, 6 voices, ~42s
s.find("e5e a5e c6e b5e a5e g5e", key="Am") # the tune: bars 3, 11, 27
s.chords(per="bar")
s.rubs()
```

The file becomes one section, `"MIDI"`. Each track's notes, or each
channel's when a track holds several, become voices named for the
track. Notes struck together with the same length form a chord, and a
note that overlaps the one before it goes to a further voice, `rh2`,
`rh3`. Onsets and lengths snap to a twelfth of a beat (`grid=12`, which
keeps sixteenths and triplets), and `grid=None` keeps every tick. The
first track's name is the title, and the first tempo, meter, and key
set the song's. A later change of meter on a barline becomes a
`time_change()`, a later tempo a `tempo_change()` at its own tick, the
sustain pedal `ped` and `lift` marks, and channel 10 a drum voice. The
piece ends at its last release or at the end of its tracks, whichever
is later. The notes enter as raw `Note` objects, each chord member
keeping its own velocity, with expression off, so saving the song
again gives back the file's notes to the grid and its tempo map.

## Engraving

```python
s.to_lilypond("piece.ly")   # then: lilypond piece.ly
```

`to_lilypond()` writes the song as LilyPond source, a text score that
diffs as well as it typesets: one staff per voice role across the
arrangement, with keys, meters and their changes, tempo marks, *rit.*
and *accel.*, pickups, chords, ties, tuplets of any size and nesting,
grace notes, dynamics and hairpins, accents, tenuto, staccato,
fermatas, arpeggios, trills, and notated pedaling. A note that
crosses a barline is split there and tied. Notes engrave as they
were written, E-flat as E-flat and D-sharp as D-sharp, and
`song.transpose()` respells them by the interval; notes from
`harmony()` take the key's spelling. A drum voice engraves on a drum
staff.
`Song(title=, composer=)` fills the header, and the MIDI file carries
the title as its track name, which the jukebox shows.

## Raw access

Notation is the front door, not the only one. `song.events()` returns
the fully expressive event stream as sorted `(tick, kind, channel, a,
b)` tuples at 480 ticks per beat, exactly what `save()` and `play()`
render, for agents that prefer to work below the notation:

```python
for tick, kind, ch, a, b in song.events():
    ...            # kind in {"on", "off", "cc64", "cc67", "tempo"}
```

Each key is well formed on its channel. A note is released no later
than the next strike of the same pitch, so a legato, fermata, or swung
note never silences the note after it, and strikes of one key at one
tick merge into one.

`Song`, `Voice`, the transforms, and the renderer are ordinary Python,
importable a la carte; a `Voice`'s `notes` list accepts hand-built
`Note` objects, which bypass notation validation. A `Note` may carry
`vels`, one velocity per pitch in the order of its `pitches`, for a
chord struck unevenly.

Query helpers answer "what notes are in this?" without a Song, so an
agent can reason about harmony directly: `chord_pitches("Cmaj9")`
returns the MIDI pitches of a chord symbol (slash bass first when
present), and `scale_pitches("Am")` returns the seven pitches of a
key's diatonic scale, ascending from the tonic. `note_pitch("c#5")`
and `note_name(61, key="Dm")` convert between written notes and MIDI
numbers for scores built programmatically; `note_name` spells for the
key (C-sharp as the leading tone of D minor, E-flat as its
Neapolitan) and writes the accidental explicitly, `n` for a natural,
so the name reads the same under any signature.

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

`save(path)` writes a type 1 Standard MIDI File: a conductor track
with the title, composer, tempo map, key and time signatures, and a
marker at each section, then one named track per voice role, so a DAW
opens each hand or instrument as its own part. `save(path,
tracks=False)` writes a single-track type 0 file, and `save(path,
only="A")` renders one section.

## Examples

| File | Demonstrates |
|---|---|
| `examples/saltarello_alla_chico.py` | the demo score: variants, per-section keys, grace notes, trill, accelerando |
| `examples/dynamo_rag.py` | a full multi-strain ragtime: stride bass, written syncopation, subdominant trio |
| `examples/silver_dollar_saloon.py` | a frontier two-step: oom-pah, honky-tonk grace slides, shave-and-a-haircut tag |
| `examples/nickelodeon.py` | a player-piano novelty roll: generated figuration, secondary-rag accents, whole-tone runs |
| `examples/player_piano_studies.py` | five Nancarrow-style studies built through the raw `Note` API: tempo canon, coprime ostinati, acceleration, full-keyboard cascades, tutti |
| `examples/minuet_small_computer.py` | sections, waltz harmony, arrangement |
| `examples/blues_416_megabytes.py` | swing, grace notes, stride, rubato |
| `examples/invention_two_processes.py` | motif transforms, two-voice counterpoint, lint |
| `examples/orrery.py` | process music: prime-period orbits, overtone pitches |
| `examples/rachmaninoff_prelude_bells.py` | a bell prelude after Rachmaninoff: fff motto chords, a chorale over a lament bass, triplet agitato, a soft-pedal coda |
| `examples/horowitz_valse_brillante.py` | a virtuoso waltz after Horowitz: an octave variation with runs, a repeated-note episode, a three-hand trio, a chromatic cadenza, an octave coda |
| `examples/rachmaninoff_elegie.py` | an elegy after Rachmaninoff: a line-cliché bass, a Neapolitan climax, the melody returned in the cello register under syncopated chords |
| `examples/horowitz_gypsy_variations.py` | variations on a gypsy dance after Horowitz's Carmen Variations: sixths, a three-hand tremolo, a nocturne, double thirds, a music box, a Presto, generated from one theme |
| `examples/rachmaninoff_prelude_alla_marcia.py` | a march prelude after Rachmaninoff: arpeggios figured with `harmony(pattern=)`, a real fermata, repeated groups, notated pedaling |
| `examples/horowitz_grand_march.py` | a Sousa-style march transcribed after Horowitz: a trombone strain, a piccolo obbligato, a dogfight break, a grandioso with a bass countermelody |
| `examples/rachmaninoff_etude_tableau.py` | a sonata-shaped étude-tableau after Rachmaninoff: a development sequenced with `transpose()`, bell chords over a falling bass, written in D minor and moved to E-flat minor with `song.transpose()` |
| `examples/horowitz_rhapsodie_hongroise.py` | a Hungarian rhapsody after Horowitz's Liszt: a recitative on the Hungarian minor, a verbunkos lassan under a cimbalom tremolo, a friska through four variations to a Prestissimo |
| `examples/rachmaninoff_sonata_movement.py` | a sonata first movement after Rachmaninoff's Second: exposition, closing group, a development sequenced by whole steps, a recapitulation with the second theme in the major, a Più mosso coda |
| `examples/horowitz_opera_fantasy.py` | an operatic paraphrase after Horowitz: an aria under a filigree, a chorus, a love duet, a galop, and a stretta that sets the aria in the bass beneath the galop |
| `examples/rachmaninoff_folia_variations.py` | eleven variations on La Folia after Rachmaninoff's Corelli Variations: a chorale voiced by dynamic programming against the bass, a three-voice fugato clean under full `lint()`, quintuplets, hemiolas, and the theme inverted in D-flat major |
| `examples/horowitz_danse_macabre.py` | a Danse macabre on the Dies irae after Horowitz: midnight, a waltz and its variations, the chant voiced by `harmonize()` over a lament bass and as a chorale, a fugato held to `lint(only=)`, a cadenza, and the cock-crow at dawn |

Running an example writes its `.mid` next to it; add `--play` to
perform it on a connected MIDI output.

## Jukebox

`jukebox.py` plays a whole folder of scores on a MIDI output. It
renders each script once (the "running a script writes its `.mid`"
contract, so a script that builds several songs contributes several
tracks) and plays the results. From a pip install it runs as
`python -m jukebox`, pointed at a folder with `--dir` or `--library`,
since its default folder is a clone's `examples` directory.

With no flag it opens the GUI (tkinter): a searchable
track list, play/stop/auto/loop, tempo/volume/voice, and a Local/Remote
toggle that sends output to a port on this machine or, over the
forwarder, to an instrument on another host. The rest are headless, for
agents and automation:

```
python jukebox.py                 # GUI
python jukebox.py --list          # print the playlist and exit
python jukebox.py --track 3       # play one track and exit
python jukebox.py --all           # play the playlist in order
python jukebox.py --dir myscores --port "FluidSynth"
python jukebox.py --library ~/midi  # a folder of MIDI files, not scripts
```

A `--library DIR` source browses a directory of existing MIDI files
instead of rendering scoremill scripts; its subfolders become named
playlists (the GUI's Genre and Category menus).

It prefers a real instrument port and warns when only a MIDI loopback
is available (which makes no sound). Real output needs `python-rtmidi`.
Re-launching is instant: a score is rebuilt only when its script has
changed or its MIDI output has gone missing, and a script that fails
reports the last line it printed.

To play an instrument attached to another machine, run the jukebox on
the far side too:

```
python jukebox.py --forward           # on the host with the instrument
python jukebox.py --remote HOST       # on the host driving playback
```

The `--remote` side streams each MIDI message over TCP to the
`--forward` side, which relays it to a local port; the driving machine
needs no MIDI hardware or backend, only `mido` to parse the scores.
The forwarder re-selects the instrument on each connection, so it may
start before the instrument is powered on. The newest connection takes
the instrument: a jukebox that connects while another holds it
displaces the old one, and the displaced jukebox reconnects at its
next play. Every departure releases all notes and both pedals,
including a client that vanishes without closing its connection,
which keepalive probes detect within about 25 seconds.

## MCP server

`mcp_server.py` exposes scoremill to an MCP client such as Claude Code
or Claude Desktop. Each build tool takes a JSON song spec, whose shape
is in the server's docstring, and returns the report, the lint
findings, the rubs, the statements of a motif (`find_motif`), a saved
MIDI file, the LilyPond source, the raw event stream, or the chord
analysis (`harmony_analysis`). `analyze_midi` reads an existing MIDI
file and returns its report, its chords, and optionally where a motif
sounds. `transform`, `harmonize_melody`, `same_shape`, `chords`,
`scale`, and `cheatsheet` cover the motif transforms and query
helpers. A `CompositionError` comes back as `{"error": ...}`.

```
pip install "scoremill[mcp]"
claude mcp add --scope user scoremill -- python -m mcp_server
```

From a clone, register `python /path/to/mcp_server.py` instead.

## License

MIT.
