"""Test suite for scoremill. Runs under pytest or directly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoremill import (CompositionError, Song, invert, retro, shift,
                       stretch)


def test_transforms():
    assert shift("c4q e4e g4e", 1) == "d4q f4e a4e"
    assert invert("c4q e4q", axis="c4") == "c4q a3q"
    assert retro("c4q e4e g4e") == "g4e e4e c4q"
    assert stretch("c4q d4e", 2) == "c4h d4q"


def test_shift_preserves_alterations():
    assert shift("g#4q", -1) == "f#4q"
    assert shift("bb3e", 2) == "db4e"


def test_invert_mirrors_alterations():
    assert invert("c#4q", axis="c4") == "cb4q"
    assert invert("bb3q", axis="g4") == "e#5q"


def test_retro_rejects_dynamics_and_ties():
    try:
        retro("!mf c4q d4q")
        raise AssertionError("dynamics check did not fire")
    except CompositionError as e:
        assert "dynamics" in str(e)
    try:
        retro("c4q~ c4q")
        raise AssertionError("tie check did not fire")
    except CompositionError as e:
        assert "ties" in str(e)


def test_mark_position_hint():
    try:
        Song().section("M").voice("m").bars(">c4q d4q e4q f4q |")
        raise AssertionError("hint did not fire")
    except CompositionError as e:
        assert "after the duration" in str(e)


def test_cresc_requires_target():
    song = Song()
    song.section("O").voice("m").bars("cresc c4q d4q e4q f4q |")
    try:
        song.report()
        raise AssertionError("cresc check did not fire")
    except CompositionError as e:
        assert "cresc" in str(e)


def test_tie_requires_same_pitch():
    song = Song()
    song.section("D").voice("m").bars("c4h~ d4h |")
    try:
        song.report()
        raise AssertionError("tie check did not fire")
    except CompositionError as e:
        assert "tie" in str(e)


def test_tie_carries_through():
    song = Song()
    song.section("T").voice("m").bars("c4h~ c4h |")
    song.arrange("T")
    events, total = song._events()
    ons = [e for e in events if e[1] == "on"]
    assert len(ons) == 1          # one sounding note, not two
    assert total == 4 * 480


def test_trill_preserves_beats():
    voice = Song().section("T").voice("m")
    voice.bars("c4h% c4h |")
    assert abs(voice.total_beats() - 4.0) < 1e-9
    pitches = [n.pitches[0] for n in voice.notes]
    assert 62 in pitches and 60 in pitches    # upper-neighbor alternation


def test_roll_staggers_onsets():
    song = Song()
    song.section("R").voice("m").bars("[c4 e4 g4]w& |")
    song.arrange("R")
    ons = [e for e in song._events()[0] if e[1] == "on"]
    assert [t for t, *_ in ons] == [0, 28, 56]


def test_grace_sounds_before_the_beat():
    song = Song()
    song.section("G").voice("m").bars("c4q +d4 e4q c4q c4q |")
    song.arrange("G")
    ons = [e for e in song._events()[0] if e[1] == "on"]
    t_grace = next(t for t, _, _, p, _ in ons if p == 62)
    t_main = next(t for t, _, _, p, _ in ons if p == 64)
    assert t_grace < t_main


def test_variant_scales_velocity():
    song = Song()
    a = song.section("A")
    a.voice("m", vel=60).bars("c4q d4q e4q f4q |")
    a.variant("A2", vel_scale=0.5)
    va = song.sections["A"].voices[0].notes[0].vel
    vb = song.sections["A2"].voices[0].notes[0].vel
    assert vb == max(15, int(va * 0.5))


def test_pickup_allows_short_first_bar():
    song = Song(pickup=1)
    voice = song.section("P").voice("m")
    voice.bars("c4q | d4q e4q f4q g4q |")
    assert abs(voice.total_beats() - 5.0) < 1e-9


def test_slash_bass_sits_below_root():
    voice = Song().section("S").voice("x")
    voice.harmony("C/G", style="block")
    assert min(voice.notes[0].pitches) % 12 == 7


def test_section_time_override():
    song = Song(time="4/4")
    sec = song.section("W", time="6/8")
    sec.voice("m").bars("c4e d4e e4e f4e g4e a4e |")
    assert sec.length_beats() == 3.0


def test_minor_key_signature():
    voice = Song(key="Dm").section("K").voice("m")
    voice.bars("b4q d5q a4q b4q |")
    assert 70 in voice.notes[0].pitches  # B-flat via the key signature


def test_tuplet_division():
    voice = Song().section("T").voice("m")
    voice.bars("{c4 d4 e4}q c4q c4h |")
    assert abs(voice.total_beats() - 4.0) < 1e-9
    assert len(voice.notes) == 5
    assert abs(voice.notes[0].beats - 1 / 3) < 1e-9


def test_ninth_chord_voicing():
    voice = Song().section("N").voice("x")
    voice.harmony("Cmaj9 Dm9 G9 Cadd9 C6", style="block")
    assert len(voice.notes[0].pitches) == 5


def test_smooth_voicing_reduces_movement():
    song = Song()
    plain = song.section("P").voice("x")
    plain.harmony("C G", style="block", voicing="plain")
    smooth = song.section("S").voice("y")
    smooth.harmony("C G", style="block", voicing="smooth")

    def movement(v):
        a, b = v.notes[0].pitches, v.notes[1].pitches
        return sum(abs(x - y) for x, y in zip(sorted(a), sorted(b)))

    assert movement(smooth) <= movement(plain)


def test_ritardando_ramp():
    song = Song(tempo=100)
    song.section("R").voice("m").bars("c4w | c4w | c4w | c4w |")
    song.ritardando("R", 2, 4, 60)
    song.arrange("R")
    tempos = [a for (_, k, _, a, _) in song._events()[0] if k == "tempo"]
    assert len(tempos) >= 8
    assert tempos[-1] < 75


def test_bar_error_reports_difference():
    try:
        Song().section("E").voice("m").bars("c4q d4q e4q |")
        raise AssertionError("bar check did not fire")
    except CompositionError as e:
        assert "short by 1.0" in str(e)
        assert "'q'" in str(e)


def test_uppercase_pitch_hint():
    try:
        Song().section("E2").voice("m").bars("C4q |")
        raise AssertionError("suggestion did not fire")
    except CompositionError as e:
        assert "lowercase" in str(e)


def test_pitch_range():
    try:
        Song().section("R1").voice("m").bars("c0q c0q c0q c0q |")
        raise AssertionError("range check did not fire")
    except CompositionError as e:
        assert "instrument range" in str(e)
    wide = Song(pitch_range=(0, 127)).section("R2").voice("m")
    wide.bars("c0q c0q c0q c0q |")
    assert wide.notes[0].pitches == [12]


def test_report_structure():
    song = Song(tempo=120)
    song.section("A").voice("m").bars("c4q e4q g4q c5q |")
    song.arrange("A")
    r = song.report()
    assert r["duration_s"] == 2.0
    assert r["sections"][0]["voices"][0]["range"] == [60, 72]


def test_lint_detects_parallel_fifths():
    song = Song()
    sec = song.section("X")
    sec.voice("a").bars("c4q d4q e4q f4q |")
    sec.voice("b").bars("g4q a4q b4q c5q |")
    song.arrange("X")
    findings = song.lint(quiet=True)
    assert any("parallel fifths" in f for f in findings)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"{name}: ok")
            except AssertionError as e:
                failures += 1
                print(f"{name}: FAILED {e}")
    sys.exit(1 if failures else 0)
