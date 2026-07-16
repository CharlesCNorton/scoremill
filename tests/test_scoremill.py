"""Test suite for scoremill. Runs under pytest or directly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jukebox
from scoremill import (CompositionError, Song, chord_pitches, invert,
                       rebar, retro, scale_pitches, shift, stretch)


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
