"""Test suite for scoremill. Runs under pytest or directly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jukebox
from scoremill import (CompositionError, Song, chord_pitches, double,
                       harmonize, invert, note_name, note_pitch, rebar, retro,
                       scale_pitches, shift, stretch, transpose,
                       transpose_chords)


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
    try:
        song.section("D").voice("m").bars("c4h~ d4h |")   # rejected at parse
        raise AssertionError("tie check did not fire")
    except CompositionError as e:
        assert "tie" in str(e)


def test_tie_mismatch_across_bars_calls():
    # A tie on a bars() call's trailing note is pending, and resolves
    # (or errors) when the next bars() call supplies the following note.
    voice = Song().section("X").voice("m")
    voice.bars("c4h c4h~ |")          # trailing tie: pending, no error yet
    try:
        voice.bars("d4h d4h |")       # resolves against d4: mismatch
        raise AssertionError("carried tie check did not fire")
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


def test_rebar_inserts_barlines():
    assert rebar("c4q d4 e4 d4 c4 d4", 3) == "c4q d4 e4 | d4 c4 d4 |"


def test_rebar_rejects_crossing_token():
    try:
        rebar("c4h d4h", 3)
        raise AssertionError("crossing check did not fire")
    except CompositionError as e:
        assert "crosses" in str(e)


def test_tuplet_admits_chords():
    voice = Song().section("TC").voice("m")
    voice.bars("{[c4 e4] d4 [c4 e4]}q c4q c4h |")
    assert abs(voice.total_beats() - 4.0) < 1e-9
    assert voice.notes[0].pitches == [60, 64]


def test_extended_chord_qualities():
    voice = Song().section("Q").voice("x")
    voice.harmony("C13 Fm11 G7b9 D7#5", style="block")
    assert len(voice.notes[0].pitches) == 5      # a thirteenth


def test_extended_dynamic_range():
    voice = Song().section("DY").voice("m")
    voice.bars("!ppp c4q !fff d4q c4h |")
    assert voice.notes[0].vel == 18
    assert voice.notes[1].vel == 96


def test_final_tie_is_laissez_vibrer():
    song = Song()
    song.section("LV").voice("m").bars("c4h c4h~ |")
    song.arrange("LV")
    song.report()          # a dangling final tie must not raise
    offs = [t for (t, k, _, _, _) in song.events() if k == "off"]
    assert max(offs) > 1920


def test_lint_locates_by_bar():
    song = Song()
    song.section("X").voice("a").bars("c4q d4q e4q f4q |")
    song.sections["X"].voice("b").bars("g4q a4q b4q c5q |")
    song.arrange("X")
    findings = song.lint(quiet=True)
    assert findings and all("bar" in f for f in findings)


def test_lint_homophonic_drops_parallels():
    song = Song()
    song.section("X").voice("a").bars("c4q d4q e4q f4q |")
    song.sections["X"].voice("b").bars("g4q a4q b4q c5q |")
    song.arrange("X")
    assert song.lint(quiet=True, mode="homophonic") == []


def test_lint_catches_held_note_collision():
    song = Song()
    song.section("H").voice("a").bars("c4w |")
    song.sections["H"].voice("b").bars("rh c4h |")
    song.arrange("H")
    findings = song.lint(quiet=True)
    assert any("bar 1 beat 3" in f for f in findings)


def test_harmony_avoid_drops_doubling():
    song = Song()
    sec = song.section("AV")
    mel = sec.voice("rh")
    mel.bars("e4w |")
    sec.voice("lh").harmony("C", style="block", avoid=mel)
    classes = {p % 12 for p in sec.voices[1].notes[0].pitches}
    assert 4 not in classes and {0, 7} <= classes


def test_soft_pedal_emits_cc67():
    song = Song()
    song.section("SP").voice("m").bars("c4w |")
    song.sections["SP"].soft()
    song.arrange("SP")
    assert "cc67" in {k for (_, k, _, _, _) in song.events()}


def test_events_exposes_raw_stream():
    song = Song(tempo=120)
    song.section("EV").voice("m").bars("c4q e4q g4q c5q |")
    song.arrange("EV")
    ev = song.events()
    assert any(k == "on" for (_, k, _, _, _) in ev)
    assert len(song._count_in_taps(4)) == 8


def test_duration_integrates_ritardando():
    song = Song(tempo=120)
    song.section("DR").voice("m").bars("c4w | c4w | c4w | c4w |")
    song.ritardando("DR", 1, 4, 60)
    song.arrange("DR")
    assert song.report()["duration_s"] > 8.0


def test_pickup_allows_full_first_bar():
    song = Song(pickup=1)
    voice = song.section("PU").voice("m")
    voice.bars("c4q d4q e4q f4q | g4q a4q b4q c5q |")
    assert abs(voice.total_beats() - 8.0) < 1e-9


def test_swing_sixteenth_unit():
    straight = Song(swing=0.5)
    straight.section("A").voice("m").bars("c4s d4s e4s f4s g4q c5h |")
    swung = Song(swing=0.66, swing_unit="sixteenth")
    swung.section("A").voice("m").bars("c4s d4s e4s f4s g4q c5h |")
    straight.arrange("A")
    swung.arrange("A")
    on_s = [t for (t, k, _, _, _) in straight.events() if k == "on"]
    on_w = [t for (t, k, _, _, _) in swung.events() if k == "on"]
    assert on_w[1] > on_s[1]      # the offbeat sixteenth is delayed


def test_chord_pitches_helper():
    assert chord_pitches("C") == [60, 64, 67]
    assert chord_pitches("Cmaj9") == [60, 64, 67, 71, 74]
    assert chord_pitches("C/G")[0] % 12 == 7          # slash bass first


def test_scale_pitches_helper():
    assert scale_pitches("C") == [60, 62, 64, 65, 67, 69, 71]
    assert scale_pitches("Am") == [69, 71, 72, 74, 76, 77, 79]
    assert scale_pitches("F")[6] == 76                # E natural in F major


def test_transpose_shifts_and_relabels():
    song = Song(key="C")
    song.section("A").voice("m").bars("c4q e4q g4q c5q |")
    song.arrange("A")
    song.transpose(3)
    assert song.sections["A"].voices[0].notes[0].pitches == [63]
    assert song.key == "Eb"


def test_transpose_range_guard():
    song = Song()
    song.section("H").voice("m").bars("a7q a7q a7q a7q |")
    song.arrange("H")
    try:
        song.transpose(24)
        raise AssertionError("range guard did not fire")
    except CompositionError as e:
        assert "range" in str(e)


def test_voicing_shell():
    voice = Song().section("S").voice("x")
    voice.harmony("Cmaj7", style="block", voicing="shell")
    assert sorted(p % 12 for p in voice.notes[0].pitches) == [0, 4, 11]


def test_voicing_rootless_drops_root():
    voice = Song().section("R").voice("x")
    voice.harmony("Cmaj9", style="block", voicing="rootless")
    assert 0 not in [p % 12 for p in voice.notes[0].pitches]


def test_voicing_drop2_widens_spread():
    drop = Song().section("D").voice("x")
    drop.harmony("Cmaj7", style="block", voicing="drop2")
    plain = Song().section("P").voice("y")
    plain.harmony("Cmaj7", style="block", voicing="plain")

    def spread(v):
        p = v.notes[0].pitches
        return max(p) - min(p)
    assert spread(drop) > spread(plain)


def test_voicing_unknown_rejected():
    try:
        Song().section("U").voice("x").harmony("C", voicing="bogus")
        raise AssertionError("voicing check did not fire")
    except CompositionError as e:
        assert "voicing" in str(e)


def test_jukebox_tempo_factor():
    assert jukebox.tempo_factor(100) == 1.0
    assert jukebox.tempo_factor(200) == 2.0
    assert jukebox.tempo_factor(50) == 0.5
    assert jukebox.tempo_factor(5) == 0.1        # clamped floor
    assert jukebox.tempo_factor(9000) == 4.0     # clamped ceiling


def test_jukebox_pretty_title():
    assert jukebox.pretty_title("a/b/silver_dollar_saloon.mid") == \
        "Silver Dollar Saloon"
    assert jukebox.pretty_title("player_piano_study_1.mid") == \
        "Player Piano Study 1"


def test_jukebox_port_selection():
    pick = jukebox.Player._auto_select
    assert pick(["Midi Through:0", "Digital Piano:1"]) == "Digital Piano:1"
    assert pick(["Midi Through:0", "Some Device"]) == "Some Device"
    assert pick(["Midi Through:0"]) == "Midi Through:0"   # loopback fallback


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


def test_retro_reverses_tuplet_members():
    assert retro("{c4 d4 e4}q f4q") == "f4q {e4 d4 c4}q"


def test_retro_keeps_grace_attached():
    assert retro("+d5 c5q e5q") == "e5q +d5 c5q"


def test_retro_writes_sticky_state_explicitly():
    assert retro("c5q d e") == "e5q d5q c5q"          # octaves explicit
    assert retro("c4e {d4 e4 f4} g4q") == "g4q {f4 e4 d4}e c4e"
    assert retro("c4q d4'") == "d4q' c4q"             # dur before marks


def test_chord_member_duration_rejected():
    try:
        Song().section("CM").voice("m").bars("[c4q e4]h [c4 e4]h |")
        raise AssertionError("member duration check did not fire")
    except CompositionError as e:
        assert "after the ']'" in str(e)


def test_chord_member_mark_rejected():
    try:
        Song().section("CM").voice("m").bars("[c4> e4]h [c4 e4]h |")
        raise AssertionError("member mark check did not fire")
    except CompositionError as e:
        assert "marks" in str(e)


def test_tuplet_member_mark_rejected():
    try:
        Song().section("TM").voice("m").bars("{c4> d4 e4}q c4q c4h |")
        raise AssertionError("tuplet member mark check did not fire")
    except CompositionError as e:
        assert "tie" in str(e)


def test_trill_too_short_rejected():
    try:
        Song().section("TR").voice("m").bars("c4s% c4s c4e c4q c4h |")
        raise AssertionError("trill length check did not fire")
    except CompositionError as e:
        assert "trill" in str(e)


def test_trill_alternates_without_stutter():
    song = Song(humanize=0, expressive=False)
    song.section("T").voice("m").bars("c4h% c4h |")
    song.arrange("T")
    trill = [n.pitches[0] for n in song.sections["T"].voices[0].notes][:-1]
    assert 62 in trill                    # the upper neighbor sounds
    assert all(a != b for a, b in zip(trill, trill[1:]))   # no repeat


def test_harmony_range_guard():
    try:
        Song().section("HR").voice("m").harmony("C", style="stride",
                                                octave=1)
        raise AssertionError("harmony range check did not fire")
    except CompositionError as e:
        assert "range" in str(e)


def test_unknown_section_reported():
    song = Song()
    song.section("A").voice("m").bars("c4w |")
    song.arrange("A")
    try:
        song.events(order=["Nope"])
        raise AssertionError("unknown section check did not fire")
    except CompositionError as e:
        assert "Nope" in str(e)


def test_duplicate_section_rejected():
    song = Song()
    song.section("A")
    try:
        song.section("A")
        raise AssertionError("duplicate section check did not fire")
    except CompositionError as e:
        assert "already exists" in str(e)


def test_harmony_slots_validated():
    try:
        Song().section("SL").voice("m").harmony("C G", slots="quarter")
        raise AssertionError("slots check did not fire")
    except CompositionError as e:
        assert "slots" in str(e)


def test_grace_needs_following_strike():
    song = Song()
    song.section("G1").voice("m").bars("c4h. e4q +g4 |")
    try:
        song.report()
        raise AssertionError("trailing grace check did not fire")
    except CompositionError as e:
        assert "grace" in str(e)
    song2 = Song()
    song2.section("G2").voice("m").bars("c4q +d4 rq e4h |")
    try:
        song2.report()
        raise AssertionError("grace-before-rest check did not fire")
    except CompositionError as e:
        assert "rest" in str(e)


def test_grace_duration_rejected():
    try:
        Song().section("GD").voice("m").bars("+d5q c5q c5q c5h |")
        raise AssertionError("grace duration check did not fire")
    except CompositionError as e:
        assert "duration" in str(e)


def test_tie_accepts_reordered_chord():
    song = Song()
    song.section("TC").voice("m").bars("[c4 e4]h~ [e4 c4]h |")
    song.arrange("TC")
    song.report()                         # must not raise
    ons = [e for e in song.events() if e[1] == "on"]
    assert len(ons) == 2                  # tie carries: one strike per pitch


def test_double_cresc_rejected():
    try:
        Song().section("DC").voice("m").bars(
            "cresc c4q dim d4q !f e4q f4q |")
        raise AssertionError("double cresc check did not fire")
    except CompositionError as e:
        assert "still open" in str(e)


def test_render_stamp_skips_and_rerenders():
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        script = os.path.join(d, "one.py")
        with open(script, "w") as fh:
            fh.write("open('one.mid','wb').write(b'x')\n"
                     "open('count.txt','a').write('.')\n")

        def runs():
            with open(os.path.join(d, "count.txt")) as fh:
                return len(fh.read())

        midis, errors = jukebox.render_scores(d)
        assert midis and not errors and runs() == 1
        jukebox.render_scores(d)              # unchanged: not re-run
        assert runs() == 1
        mtime = os.path.getmtime(script)
        os.utime(script, (mtime + 2, mtime + 2))
        jukebox.render_scores(d)              # edited: re-run
        assert runs() == 2
        jukebox.render_scores(d, force=True)  # forced: re-run
        assert runs() == 3
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_forwarder_survives_port_failures():
    import random
    import socket
    import threading
    import time
    real_get = jukebox.mido.get_output_names
    real_open = jukebox.mido.open_output
    calls = {"n": 0}

    def fake_get():
        calls["n"] += 1
        return [] if calls["n"] == 1 else ["Fake Piano"]

    def fake_open(name):
        raise RuntimeError("port busy")

    jukebox.mido.get_output_names = fake_get
    jukebox.mido.open_output = fake_open
    try:
        started = None
        for _ in range(5):                    # find a free port
            port = random.randint(21000, 39000)
            th = threading.Thread(target=jukebox.run_forwarder,
                                  args=("127.0.0.1", port), daemon=True)
            th.start()
            time.sleep(0.3)
            if th.is_alive():
                started = port
                break
        assert started, "forwarder never started"
        for _ in range(3):    # no-ports, then open-failure, then again:
            c = socket.create_connection(("127.0.0.1", started), timeout=5)
            c.close()         # each failure must leave the daemon alive
            time.sleep(0.3)
    finally:
        jukebox.mido.get_output_names = real_get
        jukebox.mido.open_output = real_open


def test_lint_catches_parallel_against_held_note():
    # Voice b holds c4 across beat 2 while the top line moves; the fifths
    # fall between the held note and the note struck against it, which a
    # shared-onset check misses and sounding-pitch sampling catches.
    song = Song()
    song.section("H").voice("a").bars("c5q g4q a4q g4q |")
    song.sections["H"].voice("b").bars("c4h d4q e4q |")
    song.arrange("H")
    findings = song.lint(quiet=True)
    assert any("parallel fifths" in f and "beat 3" in f for f in findings), \
        findings


def test_events_memoized_until_mutation():
    song = Song(tempo=120)
    sec = song.section("A")
    sec.voice("m").bars("c4q e4q g4q c5q |")
    song.arrange("A")
    first = song._events()
    assert song._events() is first          # unchanged: served from cache
    sec.voice("n").bars("e4q g4q c5q e5q |")
    assert song._events() is not first      # a new voice invalidated it
    assert song.report()["duration_s"] == 2.0


def test_cache_reflects_inplace_note_edit():
    # Editing a Note in place is the advertised raw-API path and changes
    # neither _rev nor the note count, so the render must be invalidated
    # by content, not by a count heuristic.
    song = Song(expressive=False, humanize=0)   # so velocity passes through
    voice = song.section("A").voice("m")
    voice.bars("c4q d4q e4q f4q |")
    song.arrange("A")
    assert [p for (_, k, _, p, _) in song.events() if k == "on"][0] == 60
    voice.notes[0].pitches = [72]              # raw in-place pitch edit
    assert [p for (_, k, _, p, _) in song.events() if k == "on"][0] == 72
    voice.notes[0].vel = 33                     # a non-pitch field too
    assert [b for (_, k, _, p, b) in song.events()
            if k == "on" and p == 72][0] == 33


def test_chord_pitches_matches_harmony_voice():
    # The module helper and the harmony path share one chord parser.
    for sym in ("C", "Am7", "F/A", "Cmaj9", "D7b9"):
        voice = Song().section("S").voice("x")
        voice.harmony(sym, style="block", octave=4)
        assert voice.notes[0].pitches == chord_pitches(sym, octave=4), sym


def test_stretch_any_factor():
    assert stretch("c4e", 3) == "c4q."             # 0.5 * 3 = 1.5
    assert stretch("c4q d4e", 0.5) == "c4e d4s"
    try:
        stretch("c4q", 5)                          # 5 beats: unspellable
        raise AssertionError("stretch factor check did not fire")
    except CompositionError as e:
        assert "not spellable" in str(e)


def test_report_pitch_metrics():
    s = Song(key="C")
    s.section("A").voice("m").bars("c4q e4q g4q +a4 c5q | c4q f#4q e4q c5q |")
    s.arrange("A")
    m = s.report()["sections"][0]["voices"][0]
    assert m["grace"] == 1                          # the a4 grace is counted
    assert len(m["pitch_classes"]) == 12
    assert 0 < m["out_of_key_rate"] < 1             # sounding f# is out of key
    assert isinstance(m["intervals"], dict)
    assert 0 <= m["self_similarity"] <= 1


def test_absolute_onset_anchor():
    v = Song(time="7/8").section("A").voice("m").absolute_onsets()
    v.bars("c5e d5e e5e@1 f5e g5e@2 a5e b5e |")
    assert abs(v.total_beats() - 3.5) < 1e-9
    fill = Song().section("F").voice("m").absolute_onsets()
    fill.bars("c5q d5q@3 |")                        # a rest fills to beat 3
    assert abs(fill.total_beats() - 4.0) < 1e-9
    assert fill.notes[1].pitches == []


def test_absolute_onset_optin_and_drift():
    try:
        Song().section("N").voice("m").bars("c5q@0 c5q c5q c5q |")
        raise AssertionError("opt-in check did not fire")
    except CompositionError as e:
        assert "absolute mode" in str(e)
    try:
        Song().section("D").voice("m").absolute_onsets().bars("c5h d5h@1 |")
        raise AssertionError("drift check did not fire")
    except CompositionError as e:
        assert "before the current position" in str(e)


def test_onset_anchor_carries_its_marks():
    # Marks and a grace written for an anchored note stay with it rather
    # than with the rest that fills the gap before it.
    s = Song(expressive=False, humanize=0)
    v = s.section("A").voice("m").absolute_onsets()
    v.bars("c5q ped !f +e5 d5q@3 |")
    s.arrange("A")
    s.report()                                      # the grace precedes d5
    cc = [(t, a) for (t, k, _c, a, _b) in s.events() if k == "cc64"]
    assert cc == [(3 * 480 + 10, 127), (1900, 0)]   # pressed at the anchor
    assert v.dyn_marks == {3: "f"}                  # on d5, past rest and grace
    assert "\\f" in s.to_lilypond()
    plain = Song()
    plain.section("B").voice("m").bars("c5q !f +e5 d5q e5h |")
    plain.arrange("B")
    assert "\\f" in plain.to_lilypond()             # a dynamic before a grace


def test_drum_voice():
    s = Song(time="4/4")
    k = s.section("A").drums("kit", vel=80)
    k.bars("bde hh sn hh bd hh sn hh | [bd hh]q sn hh sn |")
    s.arrange("A")
    ons = [e for e in s.events() if e[1] == "on"]
    assert {e[2] for e in ons} == {9}               # GM percussion channel
    assert {36, 38, 42} <= {e[3] for e in ons}      # bd, sn, hh
    assert s.report()["sections"][0]["voices"][0]["drum"] is True
    try:
        Song().section("Z").drums("k").bars("zzq |")
        raise AssertionError("unknown drum check did not fire")
    except CompositionError as e:
        assert "unknown drum" in str(e)


def test_lint_strict_adds_checks():
    s = Song(key="C")
    s.section("X").voice("hi").bars("g4q g4q c4q g4q |")   # dips below lo
    s.sections["X"].voice("lo").bars("e4q e4q e4q e4q |")
    s.arrange("X")
    full = s.lint(quiet=True)
    strict = s.lint(quiet=True, mode="strict")
    assert len(strict) >= len(full)
    assert any("crossing" in f for f in strict)
    try:
        s.lint(quiet=True, mode="bogus")
        raise AssertionError("mode check did not fire")
    except CompositionError as e:
        assert "strict" in str(e)


def test_lilypond_export():
    s = Song(tempo=90, time="3/4", key="F")
    s.section("A").voice("rh").bars("f4q a4q c5q | [f4 a4 c5]h.^ |")
    s.arrange("A")
    ly = s.to_lilypond()
    assert "\\version" in ly and "\\score" in ly
    assert "\\key f \\major" in ly and "\\time 3/4" in ly
    assert "\\new Staff" in ly
    assert "<f' a' c''>" in ly                      # chord, engraved


def _key_notes(song):
    """(on, off) ticks per (channel, pitch), asserting that each key's
    note-ons and note-offs alternate."""
    keys = {}
    for t, k, ch, p, _b in song.events():
        if k in ("on", "off"):
            keys.setdefault((ch, p), []).append((t, k))
    notes = {}
    for key, seq in keys.items():
        assert [k for _t, k in seq] == ["on", "off"] * (len(seq) // 2), \
            (key, seq)
        notes[key] = [(seq[i][0], seq[i + 1][0])
                      for i in range(0, len(seq), 2)]
    return notes


def test_legato_does_not_cut_a_restrike():
    song = Song(expressive=False, humanize=0)
    song.section("A").voice("m").bars("c4q_ c4q c4h |")
    song.arrange("A")
    notes = _key_notes(song)[(0, 60)]
    assert notes[1] == (480, 480 + int(480 * 0.92))   # full length


def test_swing_does_not_cut_a_restrike():
    song = Song(swing=0.64, expressive=False, humanize=0)
    song.section("A").voice("m").bars("c4e c4e c4e c4e c4h |")
    song.arrange("A")
    notes = _key_notes(song)[(0, 60)]
    assert notes[-1] == (960, 960 + int(960 * 0.92))  # the closing half note


def test_short_rolled_chord_releases_every_note():
    song = Song(expressive=False, humanize=0)
    song.section("A").voice("m").bars("[c4 e4 g4 c5 e5]s& c4s c4e c4q c4h |")
    song.arrange("A")
    notes = _key_notes(song)
    assert all(on < off for seq in notes.values() for on, off in seq)
    assert [seq[0][0] for p, seq in sorted(notes.items())
            if p[1] != 60] == [22, 44, 66, 88]        # the roll, compressed


def test_unison_strikes_merge():
    song = Song(expressive=False, humanize=0)
    sec = song.section("U")
    sec.voice("a").bars("c4w |")
    sec.voice("b").bars("c4h e4h |")
    song.arrange("U")
    assert _key_notes(song)[(0, 60)] == [(0, int(1920 * 0.92))]


def test_tempo_plan_stays_in_its_section():
    song = Song(tempo=120)
    song.section("A").voice("m").bars("c4w | c4w |")
    song.section("B").voice("m").bars("c4w | c4w |")
    song.ritardando("A", 1, 2, 60)
    song.arrange("A B")
    tempos = [(t, a) for (t, k, _c, a, _b) in song.events() if k == "tempo"]
    assert tempos[-1] == (8 * 480, 120)               # B starts a tempo


def test_step_after_ramp_takes_effect():
    song = Song(tempo=100)
    song.section("A").voice("m").bars("c4w | c4w | c4w | c4w | c4w |")
    song.ritardando("A", 1, 3, 60)
    song.tempo_change("A", 4, 120)
    song.arrange("A")
    tempos = dict((t, a) for (t, k, _c, a, _b) in song.events()
                  if k == "tempo")
    assert tempos[2 * 1920] == 60                    # the ramp's target
    assert tempos[3 * 1920] == 120                   # the later step wins


def test_cresc_keeps_accents():
    voice = Song().section("A").voice("m", vel=40)
    voice.bars("cresc c4q> d4q e4q f4q> | !f g4w |")
    assert [n.vel for n in voice.notes] == [59, 55, 62, 82, 70]


def test_tied_trill_holds_into_next_note():
    def strikes(text):
        song = Song(expressive=False, humanize=0)
        song.section("T").voice("m").bars(text)
        song.arrange("T")
        return len(_key_notes(song)[(0, 60)])
    assert strikes("c4h%~ c4h |") == strikes("c4h% c4h |") - 1
    try:
        Song().section("X").voice("m").bars("c4h%~ d4h |")
        raise AssertionError("trill tie check did not fire")
    except CompositionError as e:
        assert "tie" in str(e)


def test_trill_neighbor_stays_in_range():
    try:
        Song().section("T").voice("m").bars("c8h% c8h |")
        raise AssertionError("trill range check did not fire")
    except CompositionError as e:
        assert "range" in str(e)


def test_transpose_moves_voice_keys():
    song = Song(key="C")
    voice = song.section("A").voice("m")
    voice.bars("c4q d4q e4q f4q | g4q a4q b4q c5q |")
    song.arrange("A")
    song.transpose(3)
    assert song.report()["sections"][0]["voices"][0]["out_of_key_rate"] == 0
    voice.bars("e4q f4q g4q a4q |")                   # read in E-flat now
    assert voice.notes[-4].pitches == [63]


def test_transpose_spells_every_key():
    for key, semis, want in (("Am", -1, "G#m"), ("Cm", 1, "C#m"),
                             ("G#m", 2, "Bbm"), ("Gb", 12, "Gb")):
        song = Song(key=key)
        song.section("A").voice("m").bars("a4w |")
        song.arrange("A")
        song.transpose(semis)
        assert song.key == want, (key, semis, song.key)
        song.to_lilypond()                            # the label resolves


def test_transpose_range_error_changes_nothing():
    song = Song()
    sec = song.section("H")
    sec.voice("lo").bars("c4w |")
    sec.voice("hi").bars("a7w |")
    song.arrange("H")
    try:
        song.transpose(24)
        raise AssertionError("range guard did not fire")
    except CompositionError:
        pass
    assert sec.voices[0].notes[0].pitches == [60]


def test_variant_keeps_drums_and_meter():
    song = Song(time="4/4")
    sec = song.section("J", time="6/8")
    sec.voice("bass").bars("c2e d2e c2e d2e c2e d2e |")
    sec.drums("kit").bars("bde sne bde sne bde sne |")
    sec.variant("J2")
    song.arrange("J J2")
    j2 = song.sections["J2"]
    assert [v.drums for v in j2.voices] == [False, True]
    assert j2.time_sig == "6/8"
    assert song.lint(quiet=True, mode="homophonic") == []
    assert "\\time 4/4" not in song.to_lilypond()


def test_pickup_aligns_bar_effects():
    song = Song(tempo=100, time="3/4", pickup=1, humanize=0)
    sec = song.section("A")
    sec.voice("m", vel=50).bars("c4q | e4q e4q e4q | e4q e4q e4q |")
    sec.pedal("bar")
    song.tempo_change("A", 2, 50)
    song.arrange("A")
    ev = song.events()
    assert [t for (t, k, _c, _p, b) in ev if k == "on" and b == 53] \
        == [480, 1920]                                # the two downbeats
    assert [t for (t, k, _c, a, _b) in ev if k == "cc64" and a == 127] \
        == [10, 490, 1930]                            # pickup, bar 1, bar 2
    assert next(t for (t, k, _c, a, _b) in ev
                if k == "tempo" and a == 50) == 1920


def test_swing_follows_a_half_beat_pickup():
    song = Song(swing=0.64, pickup=0.5, expressive=False, humanize=0)
    song.section("A").voice("m").bars(
        "g4e | c5e d5e e5e f5e g5e a5e b5e c6e |")
    song.arrange("A")
    ons = [t for (t, k, _c, _p, _b) in song.events() if k == "on"]
    assert ons[:4] == [67, 240, 547, 720]             # offbeats swing


def test_pedal_lift_stays_inside_its_section():
    song = Song()
    a = song.section("A")
    a.voice("m").bars("c4w |")
    a.pedal(1.5)
    b = song.section("B")
    b.voice("m").bars("e4w |")
    b.pedal("bar")
    song.arrange("A B")
    cc = [(t, v) for (t, k, _c, v, _b) in song.events() if k == "cc64"]
    assert (1900, 0) in cc and (1930, 127) in cc
    assert not any(1930 < t < 3820 for t, _v in cc)   # B's pedal holds


def test_harmony_follows_the_section_pickup():
    song = Song(pickup=1)
    a = song.section("A")
    a.voice("rh").bars("g4q | c5q d5q e5q f5q |")
    a.voice("lh").harmony("C")
    b = song.section("B")
    b.voice("rh").bars("c5q d5q e5q f5q |")
    b.voice("lh").harmony("C")
    song.arrange("A B")
    song.report()                                     # lengths agree
    assert a.voices[1].notes[0].pitches == []         # A's pickup rest
    assert b.voices[1].notes[0].pitches != []         # B opens on beat 1


def test_harmony_before_melody_still_fits_a_downbeat_section():
    song = Song(pickup=1)
    b = song.section("B")
    b.voice("lh").harmony("C G7")                 # written first: guesses
    b.voice("rh").bars("c5q d5q e5q f5q | g5w |") # opens on a downbeat
    song.arrange("B")
    song.report()                                 # the guessed rest yields
    assert b.voices[0].notes[0].pitches != []
    a = Song(pickup=1).section("A")
    a.voice("lh").harmony("C")
    a.voice("rh").bars("g4q | c5q d5q e5q f5q |") # a pickup: the rest stays
    assert a.length_beats() == 5.0


def test_lilypond_tuplets_and_pickups():
    s = Song(pickup=1)
    s.section("A").voice("m").bars(
        "g4q | {c4 d4 e4 f4 g4}q {a4 b4 c5}q c5h |")
    s.arrange("A")
    ly = s.to_lilypond()
    assert "\\partial 4" in ly
    assert "\\tuplet 5/4 { c'16 d'16 e'16 f'16 g'16 }" in ly
    assert "\\tuplet 3/2 { a'8 b'8 c''8 }" in ly


def test_lilypond_splits_lengths_with_no_single_value():
    s = Song(time="5/4")
    sec = s.section("A")
    sec.voice("rh").bars("c5h. e5h |")
    sec.voice("lh").harmony("C", style="block")      # a 5-beat chord
    s.arrange("A")
    assert "<c e g>1~ <c e g>4" in s.to_lilypond()


def test_lilypond_drum_staff():
    s = Song()
    s.section("A").drums("kit").bars("bde hh sn hh [bd hh]q snq |")
    s.arrange("A")
    ly = s.to_lilypond()
    assert "\\new DrumStaff" in ly and "\\drummode" in ly
    assert "bd8 hh8 sn8 hh8 <bd hh>4 sn4" in ly


def test_double_dotted_durations():
    voice = Song().section("D").voice("m")
    voice.bars("c4q.. c4s c4h |")
    assert [n.beats for n in voice.notes] == [1.75, 0.25, 2.0]
    assert stretch("c4q..", 2) == "c4h.."


def test_repetition_of_tokens_and_groups():
    voice = Song().section("R").voice("m")
    voice.bars("c4e*8 | (d4e e4e)*4 | (f4q g4q a4q b4q |)*2")
    assert len(voice.notes) == 24 and abs(voice.total_beats() - 16) < 1e-9
    try:
        Song().section("U").voice("m").bars("(c4e d4e c4q c4h |")
        raise AssertionError("unbalanced group check did not fire")
    except CompositionError as e:
        assert "group" in str(e)


def test_notated_pedaling():
    song = Song()
    song.section("P").voice("m").bars("ped c4h e4h | ped g4h lift c5h |")
    song.arrange("P")
    cc = [(t, v) for (t, k, _c, v, _b) in song.events() if k == "cc64"]
    assert cc == [(10, 127), (1900, 0), (1930, 127), (2860, 0)]


def test_fermata_holds_time():
    song = Song(tempo=60, fermata=1.5)
    song.section("F").voice("m").bars("c4h c4h^ |")
    song.section("G").voice("m").bars("c4w |")
    song.arrange("F G")
    assert song.report()["duration_s"] == 2 + 3 + 4    # the hold, then a tempo


def test_fermata_on_a_rest_is_a_pause():
    song = Song(tempo=60, fermata=2.0)
    song.section("P").voice("m").bars("c4h rh^ |")
    song.arrange("P")
    assert song.report()["duration_s"] == 2 + 4


def test_harmony_pattern_figures_the_ladder():
    voice = Song().section("H").voice("x")
    voice.harmony("C", octave=3, pattern="0 2 4 2", unit=0.5)
    assert [n.pitches for n in voice.notes][:4] == [[48], [55], [64], [55]]
    trip = Song().section("T").voice("x")
    trip.harmony("C G/B", slots="half", octave=2, pattern="0 1 2", unit=1 / 3)
    assert len(trip.notes) == 12 and trip.notes[6].pitches == [35]  # the B
    for bad, word in (("0 x", "pattern step"), ("0 99", "ladder")):
        try:
            Song().section("E").voice("x").harmony("C", pattern=bad)
            raise AssertionError("pattern check did not fire")
        except CompositionError as e:
            assert word in str(e)


def test_transpose_fragment_spells_by_interval():
    assert transpose("b4q c5e d#5e", 3) == "dn5q eb5e f#5e"
    assert transpose("bb4q e5 f#5", -1, key="F") == "an4q d#5 e#5"
    assert transpose("c4q", 12) == "cn5q"


def test_double_adds_octaves_and_thirds():
    assert double("a4q d5q. e5e", -7) == "[a3 a4]q [d4 d5]q. [e4 e5]e"
    assert double("c4q e g |", 7) == "[c4 c5]q [e4 e5] [g4 g5] |"
    assert double("c#5q", -7) == "[c#4 c#5]q"          # an exact octave
    assert double("f5q e5", -2) == "[d5 f5]q [c5 e5]"  # thirds in the key
    assert double("{c4 d4 e4}q +f4 g4q c5e@2", 7) == \
        "{[c4 c5] [d4 d5] [e4 e5]}q +f4 [g4 g5]q [c5 c6]e@2"
    v = Song(key="Dm", time="3/4").section("A").voice("m")
    v.bars(double("f5q e5q d5q | c#5h. |", -2))
    assert v.notes[3].pitches == [69, 73]               # a4 under c#5
    try:
        double("c5h% c5h", 7)
        raise AssertionError("trill check did not fire")
    except CompositionError as e:
        assert "trill" in str(e)


def test_harmonize_voices_cleanly_against_the_bass():
    mel = ("a4q d5q. e5e | f5q e5q. d5e | c#5q d5q. a4e | b4q c5q. g4e |"
           " a4q f5q. e5e | c5q g5q. f5e | e5q d5q. f5e | e5h. |")
    bass = ("d3q f3q bb2q | a2q c#3q e3q | a2q d3q f3q | e3q c3q bb2q |"
            " f2q a2q c3q | e3q c3q g2q | a2q f3q d3q | e3q a2q c#3q |")
    for voices in (2, 3, 4):
        out = harmonize(mel, "Dm A7 Dm C7 F C Dm A", key="Dm",
                        voices=voices, bass=bass)
        s = Song(time="3/4", key="Dm")
        sec = s.section("C")
        sec.voice("rh").bars(out)
        sec.voice("lh").bars(bass)
        s.arrange("C")
        assert s.lint(quiet=True) == [], voices     # no parallels at all
        assert all(len(n.pitches) == voices for n in sec.voices[0].notes)


def test_harmonize_passes_marks_and_keeps_ties():
    out = harmonize("!p c5h~ c5q +d5 e5q | rq g5q.% f5e e5q |", "C G7")
    assert out.startswith("!p [") and "+d5" in out and "g5q.%" in out
    v = Song().section("T").voice("m")
    v.bars(out)                                    # the tie holds its chord
    assert v.notes[0].pitches == v.notes[1].pitches
    assert harmonize("c5q d5 e5 f5 |", "C G7", slots=2).count("[") == 4
    try:
        harmonize("c5q d5q e5q f5q | g5w |", "C")
        raise AssertionError("symbol count check did not fire")
    except CompositionError as e:
        assert "chord symbols" in str(e)


def test_note_pitch_and_name():
    assert note_pitch("c#5") == 73
    assert note_pitch("b4", key="F") == 70             # the signature applies
    assert note_pitch("bn4", key="F") == 71
    assert note_name(61, "Dm") == "c#4"                 # the leading tone
    assert note_name(63, "Dm") == "eb4"                 # the Neapolitan
    assert note_name(71, "Gb") == "cb5" and note_name(65, "F#") == "e#4"
    assert note_name(60) == "cn4"                       # explicit natural
    for key in ("C", "Dm", "Gb", "F#", "Bbm", "E"):
        for p in range(21, 109):
            assert note_pitch(note_name(p, key)) == p, (key, p)
    try:
        note_pitch("c#")
        raise AssertionError("octave check did not fire")
    except CompositionError as e:
        assert "octave" in str(e)


def test_transpose_chords_spells_consistently():
    assert transpose_chords("C G7/B Am*2 . | F/A", 1) == \
        "Db Ab7/C Bbm*2 . | Gb/Bb"
    assert transpose_chords("Dm A7 Bb Gm/Bb", 3) == "Fm C7 Db Bbm/Db"
    assert transpose_chords("Am E7", 4, key="C#m") == "C#m G#7"
    v = Song().section("A").voice("x")
    v.harmony(transpose_chords("C G7", 2))
    assert v.notes[0].pitches == chord_pitches("D", 3)


def test_harmony_slots_by_the_beat():
    v = Song(time="3/4").section("A").voice("x")
    v.harmony("Dm A7 .", slots=1)                      # i-V split 1 + 2
    assert [n.beats for n in v.notes] == [1.0, 1.0, 1.0]
    assert v.notes[1].pitches == chord_pitches("A7", 3)
    w = Song(time="5/16").section("B").voice("x")
    w.harmony("C G", style="alberti")                  # slots of 1.25 beats
    assert abs(w.total_beats() - 2.5) < 1e-9


def test_lint_only_one_section():
    s = Song()
    a = s.section("A")
    a.voice("x").bars("c4q d4q e4q f4q |")
    a.voice("y").bars("g4q a4q b4q c5q |")
    b = s.section("B")
    b.voice("x").bars("c4w |")
    b.voice("y").bars("e4w |")
    s.arrange("A B")
    assert s.lint(quiet=True, only="B") == []
    assert s.lint(quiet=True, only=["A"])            # the parallels in A
    try:
        s.lint(quiet=True, only="Z")
        raise AssertionError("section check did not fire")
    except CompositionError as e:
        assert "Z" in str(e)


def test_chords_names_the_harmony():
    s = Song(key="C")
    a = s.section("A")
    a.voice("rh").bars("e5q g5q c6h | d5q f5q b5h |")
    a.voice("lh").harmony("C G7", octave=2, pattern="0 2 4 2", unit=0.5)
    s.arrange("A")
    assert [c["chord"] for c in s.chords(per="bar")] == ["C", "G7"]
    minor = Song(key="Am")
    minor.section("M").voice("x").harmony("Am Dm/F E7 Am", octave=3)
    minor.arrange("M")
    assert [c["chord"] for c in minor.chords(per="bar")] == \
        ["Am", "Dm/F", "E7", "Am"]


def test_cresc_follows_time_not_note_count():
    voice = Song().section("C").voice("m", vel=40)
    voice.bars("cresc c4h% c4q c4q | !f c4w |")
    after_trill = voice.notes[-3]                 # the quarter on beat 3
    assert after_trill.vel == int(40 + (70 - 40) * 3 / 4)


def test_title_and_composer_metadata():
    s = Song(title="Evening", composer="An Agent")
    s.section("A").voice("m").bars("c4w |")
    s.arrange("A")
    mid = s._midifile()
    names = [m.name for m in mid.tracks[0] if m.type == "track_name"]
    assert names == ["Evening"]
    ly = s.to_lilypond()
    assert 'title = "Evening"' in ly and 'composer = "An Agent"' in ly


def test_program_changes_per_section():
    s = Song()
    s.section("A").voice("m", program=0).bars("c4w |")
    s.section("B").voice("m", program=40).bars("c4w |")
    s.arrange("A B")
    progs = []
    t = 0
    for msg in jukebox.mido.merge_tracks(s._midifile().tracks):
        t += msg.time
        if msg.type == "program_change":
            progs.append((t, msg.program))
    assert progs == [(0, 0), (1920, 40)]


def test_strict_lint_flags_unreachable_chords():
    s = Song()
    sec = s.section("W")
    sec.voice("lh").bars("[c3 e4]q [c3 g4]q [c3 g4]h& |")   # 10th ok, 12th not
    s.arrange("W")
    wide = [f for f in s.lint(quiet=True, mode="strict") if "wide chord" in f]
    assert len(wide) == 1                         # the rolled one is fine


def test_septuplets_do_not_drift():
    s = Song()
    sec = s.section("S")
    sec.voice("m").bars("{c4 d4 e4 f4 g4 a4 b4}q*4 | c5w |")
    s.arrange("S")
    ons = sorted(t for (t, k, _c, _p, _b) in s.events() if k == "on")
    assert 1920 in ons                            # bar 2 lands exactly


def test_lilypond_engraves_expression():
    s = Song(tempo=80, time="4/4", key="C")
    sec = s.section("E")
    sec.voice("rh").bars("!p ped c5q> d5q_ cresc e5q' f5q | !f g5h% lift"
                         " c6h^ |")
    s.ritardando("E", 2, 3, 60)
    s.arrange("E")
    ly = s.to_lilypond()
    for mark in ("\\p", "\\<", "\\f", "->", "--", "-.", "\\trill",
                 "\\fermata", "\\sustainOn", "\\sustainOff", 'tempo "rit."'):
        assert mark in ly, mark


def test_lilypond_ramp_word_follows_the_prevailing_tempo():
    s = Song(tempo=100)
    s.section("R").voice("m").bars("c4w | c4w | c4w | c4w |")
    s.tempo_change("R", 1, 60)
    s.ritardando("R", 2, 4, 90)                    # 60 rising to 90
    s.arrange("R")
    ly = s.to_lilypond()
    assert 'tempo "accel."' in ly and "rit." not in ly


def test_lilypond_keeps_written_spelling():
    s = Song(key="C")
    s.section("S").voice("m").bars("c4q eb4q d#4q +bb4 cb5q |")
    s.arrange("S")
    ly = s.to_lilypond()
    assert "ef'4" in ly and "ds'4" in ly and "bf'8" in ly and "cf''4" in ly
    s.transpose(2)                        # respelled by the interval
    ly = s.to_lilypond()
    assert "f'4" in ly and "es'4" in ly and "df''4" in ly


def test_lilypond_piano_staff_and_bass_clef():
    s = Song(key="C")
    a = s.section("A")
    a.voice("rh").bars("e5q g5q c6h |")
    a.voice("lh").harmony("C", octave=2, pattern="0 2 4 2", unit=0.5)
    s.arrange("A")
    ly = s.to_lilypond()
    assert "\\new PianoStaff" in ly
    assert ly.count("\\clef bass") == 1            # the left hand only


def test_section_swing_overrides_the_song():
    s = Song(swing=0.5, expressive=False, humanize=0)
    s.section("STRAIGHT").voice("m").bars("c4e d4e e4e f4e g4h |")
    s.section("SWUNG").voice("m").bars("c4e d4e e4e f4e g4h |")
    s.sections["SWUNG"].swing(0.66)
    s.arrange("STRAIGHT SWUNG")
    ons = [t for (t, k, _c, _p, _b) in s.events() if k == "on"]
    assert ons[1] == 240                         # straight offbeat
    assert ons[6] == 1920 + 240 + int(0.16 * 480)  # swung offbeat


def test_song_dynamics_retune_the_levels():
    voice = Song(dynamics={"p": 50, "f": 90}).section("D").voice("m")
    voice.bars("!p c4q !f d4q !mf e4q f4q |")
    assert [n.vel for n in voice.notes] == [50, 90, 58, 58]
    try:
        Song(dynamics={"loud": 99})
        raise AssertionError("dynamics check did not fire")
    except CompositionError as e:
        assert "dynamics" in str(e)


def test_random_songs_through_every_path():
    # Seeded random songs mixing tuplets, chords, graces, trills, ties,
    # fermatas, pedal marks, pickups, swing, rubato, ramps, and figured
    # harmony must render, analyze, lint, engrave, and transpose, with
    # every key's note-ons and note-offs alternating.
    import random
    rng = random.Random(11)
    durs = [("q", 1.0), ("e", 0.5), ("h", 2.0), ("s", 0.25), ("q.", 1.5),
            ("e.", 0.75), ("q..", 1.75)]

    def pitch():
        return (rng.choice("cdefgab") + rng.choice(["", "", "#", "b", "n"])
                + str(rng.randint(3, 5)))

    def bar(beats):
        out, left = [], beats
        while left > 1e-9:
            d, v = rng.choice([x for x in durs if x[1] <= left + 1e-9])
            r = rng.random()
            if r < 0.08 and left >= 1:
                out.append("{" + " ".join(pitch() for _ in range(3)) + "}q")
                left -= 1
                continue
            mark = rng.choice(["", "", ">", "'", "_", "^", "&"])
            if r < 0.25:
                tok = "[" + " ".join(pitch() for _ in range(3)) + "]"
            elif r < 0.32:
                tok, mark = "r", rng.choice(["", "^"])
            else:
                tok = pitch()
                if v >= 1 and rng.random() < 0.1:
                    mark = "%"
                if rng.random() < 0.08:
                    out.append("+" + pitch())
            if rng.random() < 0.05:
                out.append(rng.choice(["!p", "!f", "ped", "lift"]))
            out.append(f"{tok}{d}{mark}")
            left -= v
        return " ".join(out)

    for _trial in range(40):
        bpb = rng.choice([2, 3, 4])
        s = Song(time=f"{bpb}/4", key=rng.choice(["C", "F", "Am", "E"]),
                 humanize=rng.choice([0, 1]), swing=rng.choice([0.5, 0.62]),
                 pickup=rng.choice([0, 1]))
        names = []
        for k in range(rng.randint(1, 3)):
            sec = s.section(f"S{k}")
            nbars = rng.randint(1, 3)
            for vname in ("rh", "lh")[:rng.randint(1, 2)]:
                if rng.random() < 0.3:
                    sec.voice(vname).harmony(
                        " ".join(rng.choice(["C", "Am", "F/A", "G7"])
                                 for _ in range(nbars)), octave=2,
                        pattern=rng.choice([None, "0 2 4 2"]),
                        unit=rng.choice([0.5, 1 / 3]))
                else:
                    sec.voice(vname).bars(
                        " | ".join(bar(bpb) for _ in range(nbars)) + " |")
            if rng.random() < 0.3:
                s.ritardando(f"S{k}", 1, nbars + 1, 50)
            names.append(f"S{k}")
        s.arrange(" ".join(names))
        s.report()
        s.lint(quiet=True, mode="strict")
        s.chords()
        s.to_lilypond()
        s.transpose(rng.choice([-3, 2]))
        s.to_lilypond()
        _key_notes(s)


class _FakeOut:
    """A stand-in MIDI output that records what it is sent."""

    def __init__(self, name="Fake Piano"):
        self.name = name
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)

    def close(self):
        pass


def _start_forwarder(outs):
    """Run a forwarder on a free loopback port whose instrument is a
    fresh _FakeOut per connection, appended to `outs`. Returns the port
    and a function that restores mido."""
    import socket
    import threading
    import time
    real = (jukebox.mido.get_output_names, jukebox.mido.open_output)

    def fake_open(name):
        outs.append(_FakeOut(name))
        return outs[-1]

    jukebox.mido.get_output_names = lambda: ["Fake Piano"]
    jukebox.mido.open_output = fake_open
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    threading.Thread(target=jukebox.run_forwarder,
                     args=("127.0.0.1", port), daemon=True).start()
    time.sleep(0.3)

    def restore():
        jukebox.mido.get_output_names, jukebox.mido.open_output = real
    return port, restore


def test_jukebox_title_from_track_name():
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        s = Song(title="Evening Song")
        s.section("A").voice("m").bars("c4w |")
        s.arrange("A")
        titled = s.save(os.path.join(d, "07_evening.mid"))
        plain = Song()
        plain.section("A").voice("m").bars("c4w |")
        plain.arrange("A")
        untitled = plain.save(os.path.join(d, "08_quiet_night.mid"))
        assert jukebox.midi_title(titled) == "Evening Song"
        assert jukebox.midi_title(untitled) == "Quiet Night"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_jukebox_release_lifts_soft_pedal():
    out = _FakeOut()
    jukebox.release_all(out)
    assert {(m.channel, m.control, m.value) for m in out.sent} == \
        {(ch, cc, 0) for ch in range(16) for cc in (64, 67, 123)}


def test_jukebox_voice_leaves_drum_channel():
    real = (jukebox.mido.get_output_names, jukebox.mido.open_output)
    out = _FakeOut()
    jukebox.mido.get_output_names = lambda: ["Fake Piano"]
    jukebox.mido.open_output = lambda name: out
    try:
        jukebox.Player().set_voice(40)
        chans = {m.channel for m in out.sent if m.type == "program_change"}
        assert 9 not in chans and len(chans) == 15
    finally:
        jukebox.mido.get_output_names, jukebox.mido.open_output = real


def test_render_stamp_rerenders_missing_output():
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "one.py"), "w") as fh:
            fh.write("open('one.mid','wb').write(b'x')\n"
                     "open('count.txt','a').write('.')\n")
        jukebox.render_scores(d)
        os.remove(os.path.join(d, "one.mid"))
        midis, _errors = jukebox.render_scores(d)     # output gone: re-run
        with open(os.path.join(d, "count.txt")) as fh:
            assert len(fh.read()) == 2
        assert midis
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_render_reports_the_script_error():
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "bad.py"), "w") as fh:
            fh.write("raise SystemExit('bar 3: short by 1.0 beats')\n")
        _midis, errors = jukebox.render_scores(d)
        assert errors and "short by 1.0 beats" in errors[0], errors
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_forwarder_keepalive_option():
    import socket
    s = socket.socket()
    try:
        jukebox._keepalive(s)
        assert s.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
    finally:
        s.close()


def test_forwarder_newest_client_takes_instrument():
    import socket
    import time
    outs = []
    port, restore = _start_forwarder(outs)
    try:
        idle = socket.create_connection(("127.0.0.1", port))
        time.sleep(0.3)
        live = socket.create_connection(("127.0.0.1", port))
        live.sendall(bytes([0x90, 60, 64]))           # note_on C4
        time.sleep(0.5)
        assert len(outs) == 2
        released = {(m.channel, m.control) for m in outs[0].sent
                    if m.type == "control_change"}
        assert {(ch, cc) for ch in range(16) for cc in (64, 67, 123)} \
            <= released                               # idle client let go
        assert any(m.type == "note_on" for m in outs[1].sent)
        idle.close()
        live.close()
    finally:
        restore()


def test_network_output_reconnects_after_displacement():
    import time
    outs = []
    port, restore = _start_forwarder(outs)
    try:
        a = jukebox.NetworkOutput("127.0.0.1", port)
        time.sleep(0.3)
        b = jukebox.NetworkOutput("127.0.0.1", port)  # displaces a
        time.sleep(0.3)
        a.reconnect()                                 # a takes it back
        time.sleep(0.3)
        a.send(jukebox.mido.Message("note_on", note=62, velocity=50))
        time.sleep(0.3)
        assert len(outs) == 3
        assert any(m.type == "note_on" and m.note == 62
                   for m in outs[2].sent)
        a.close()
        b.close()
    finally:
        restore()


def test_player_reports_a_lost_forwarder():
    import shutil
    import tempfile
    import threading
    import time
    outs = []
    port, restore = _start_forwarder(outs)
    d = tempfile.mkdtemp()
    try:
        song = Song(tempo=120)
        song.section("A").voice("m").bars(
            "c4q d4q e4q f4q | g4q a4q b4q c5q |")
        song.arrange("A")
        path = song.save(os.path.join(d, "t.mid"))
        lost = threading.Event()
        player = jukebox.Player(remote=("127.0.0.1", port),
                                on_lost=lost.set)
        player.play(path)
        time.sleep(0.6)
        other = jukebox.NetworkOutput("127.0.0.1", port)   # takes over
        assert lost.wait(4.0)
        player.close()
        other.close()
    finally:
        restore()
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"{name}: ok")
            except Exception as e:          # an error fails the test too
                failures += 1
                print(f"{name}: FAILED {type(e).__name__}: {e}")
    sys.exit(1 if failures else 0)
