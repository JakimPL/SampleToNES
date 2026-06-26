from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_shared.constants.project import REFERENCE_NES_FREQUENCY, REFERENCE_TEMPO
from tests.sampletones_application.logic.sequencer.playback.conftest import (
    add_sample,
    make_controller,
    make_pulse_reconstruction,
    place_modifier_row,
    place_row,
)
from tests.suite.scenario import BaseTestScenario, ScenarioStep


@dataclass
class SynthesizerContext:
    synthesizer: RowSynthesizer
    chunks: list[np.ndarray] = field(default_factory=list)
    tick_snapshots: dict[str, int] = field(default_factory=dict)
    sample_id_snapshots: dict[str, Optional[str]] = field(default_factory=dict)


def _make_context() -> SynthesizerContext:
    controller = make_controller()
    return SynthesizerContext(synthesizer=RowSynthesizer(controller, Config()))


def _controller(context: SynthesizerContext):
    return context.synthesizer._project_controller


def _state(context: SynthesizerContext, generator: GeneratorName = GeneratorName.PULSE1):
    return context.synthesizer._channel_states[generator]


def _render(context: SynthesizerContext) -> np.ndarray:
    audio, _ = context.synthesizer.render_row()
    context.chunks.append(audio)
    return audio


class TestTriggerSetsDefaults:
    def test_transpose_and_volume_default_to_zero_and_max(self) -> None:
        def place_pulse_sample_on_row_0(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(pitch=60, volume=15, count=4)
            sample = add_sample(_controller(context), recon)
            place_row(_controller(context), generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)

        def render_row_0_and_assert_defaults(context: SynthesizerContext) -> None:
            _render(context)
            assert _state(context).transpose == 0
            assert _state(context).volume == MAX_VOLUME

        BaseTestScenario(
            label="trigger sets default transpose and volume",
            build=_make_context,
            steps=[
                ScenarioStep(label="place pulse sample on row 0", action=place_pulse_sample_on_row_0),
                ScenarioStep(label="render row 0 — assert defaults", action=render_row_0_and_assert_defaults),
            ],
        ).run()

    def test_explicit_transpose_and_volume_from_row(self) -> None:
        def place_pulse_sample_with_modifiers(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=4)
            sample = add_sample(_controller(context), recon)
            place_row(
                _controller(context),
                generator=GeneratorName.PULSE1,
                row_index=0,
                sample_id=sample.id,
                transpose=5,
                volume=8,
            )

        def render_row_0_and_assert_explicit_values(context: SynthesizerContext) -> None:
            _render(context)
            assert _state(context).transpose == 5
            assert _state(context).volume == 8

        BaseTestScenario(
            label="trigger with explicit modifiers",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place pulse sample with transpose=5 volume=8", action=place_pulse_sample_with_modifiers
                ),
                ScenarioStep(
                    label="render row 0 — assert explicit values", action=render_row_0_and_assert_explicit_values
                ),
            ],
        ).run()


class TestSustain:
    def test_empty_row_continues_previous_note(self) -> None:
        def place_pulse_sample_on_row_0(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=12)
            sample = add_sample(_controller(context), recon)
            place_row(_controller(context), generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)

        def render_row_0_and_record_state(context: SynthesizerContext) -> None:
            _render(context)
            context.tick_snapshots["after_row_0"] = _state(context).tick_index
            context.sample_id_snapshots["triggered"] = _state(context).sample_id
            assert _state(context).sample_id is not None

        def render_empty_row_1_and_assert_tick_advanced(context: SynthesizerContext) -> None:
            _render(context)
            assert _state(context).tick_index > context.tick_snapshots["after_row_0"]
            assert _state(context).sample_id == context.sample_id_snapshots["triggered"]

        BaseTestScenario(
            label="sustain — empty row continues previous note",
            build=_make_context,
            steps=[
                ScenarioStep(label="place pulse sample on row 0", action=place_pulse_sample_on_row_0),
                ScenarioStep(label="render row 0 — note triggers", action=render_row_0_and_record_state),
                ScenarioStep(
                    label="render row 1 (empty) — note sustains", action=render_empty_row_1_and_assert_tick_advanced
                ),
            ],
        ).run()


class TestModifierOnlyRow:
    def test_volume_zero_silences_without_retriggering(self) -> None:
        def setup(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=12)
            sample = add_sample(_controller(context), recon)
            place_row(
                _controller(context),
                generator=GeneratorName.PULSE1,
                row_index=0,
                sample_id=sample.id,
                volume=15,
            )
            place_modifier_row(
                _controller(context),
                generator=GeneratorName.PULSE1,
                row_index=1,
                volume=0,
            )

        def render_row_0_and_record_state(context: SynthesizerContext) -> None:
            _render(context)
            context.tick_snapshots["after_row_0"] = _state(context).tick_index
            context.sample_id_snapshots["after_row_0"] = _state(context).sample_id
            assert _state(context).volume == 15

        def render_modifier_row_and_assert_volume_changed(context: SynthesizerContext) -> None:
            _render(context)
            assert _state(context).volume == 0
            assert _state(context).sample_id == context.sample_id_snapshots["after_row_0"]
            assert _state(context).tick_index > context.tick_snapshots["after_row_0"]

        BaseTestScenario(
            label="modifier-only row changes volume without retriggering",
            build=_make_context,
            steps=[
                ScenarioStep(label="place sample on row 0, modifier on row 1", action=setup),
                ScenarioStep(label="render row 0 — volume=15", action=render_row_0_and_record_state),
                ScenarioStep(
                    label="render row 1 — volume drops to 0, no retrigger",
                    action=render_modifier_row_and_assert_volume_changed,
                ),
            ],
        ).run()

    def test_transpose_updates_without_retriggering(self) -> None:
        def setup(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=12)
            sample = add_sample(_controller(context), recon)
            place_row(
                _controller(context),
                generator=GeneratorName.PULSE1,
                row_index=0,
                sample_id=sample.id,
                transpose=0,
            )
            place_modifier_row(
                _controller(context),
                generator=GeneratorName.PULSE1,
                row_index=1,
                transpose=7,
            )

        def render_row_0_and_record_sample(context: SynthesizerContext) -> None:
            _render(context)
            context.sample_id_snapshots["triggered"] = _state(context).sample_id
            assert _state(context).transpose == 0

        def render_modifier_row_and_assert_transpose_changed(context: SynthesizerContext) -> None:
            _render(context)
            assert _state(context).transpose == 7
            assert _state(context).sample_id == context.sample_id_snapshots["triggered"]

        BaseTestScenario(
            label="modifier-only row changes transpose without retriggering",
            build=_make_context,
            steps=[
                ScenarioStep(label="place sample on row 0, transpose modifier on row 1", action=setup),
                ScenarioStep(label="render row 0 — transpose=0", action=render_row_0_and_record_sample),
                ScenarioStep(
                    label="render row 1 — transpose=7, no retrigger",
                    action=render_modifier_row_and_assert_transpose_changed,
                ),
            ],
        ).run()


class TestChannelMask:
    def test_masked_channel_produces_silence(self) -> None:
        def place_pulse_sample(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=4)
            sample = add_sample(_controller(context), recon)
            place_row(_controller(context), generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)

        def set_mask_excluding_pulse1(context: SynthesizerContext) -> None:
            context.synthesizer.set_channel_mask(frozenset(GeneratorName.items()) - {GeneratorName.PULSE1})

        def render_and_compare_against_unmasked(context: SynthesizerContext) -> None:
            audio_masked = _render(context)

            unmasked_synthesizer = RowSynthesizer(_controller(context), Config())
            unmasked_synthesizer.set_channel_mask(frozenset({GeneratorName.PULSE1}))
            audio_with_pulse1, _ = unmasked_synthesizer.render_row()

            assert not np.allclose(audio_masked, audio_with_pulse1)

        BaseTestScenario(
            label="masked channel excluded from mix",
            build=_make_context,
            steps=[
                ScenarioStep(label="place pulse sample on row 0", action=place_pulse_sample),
                ScenarioStep(label="mask out PULSE1", action=set_mask_excluding_pulse1),
                ScenarioStep(
                    label="render and assert differs from unmasked", action=render_and_compare_against_unmasked
                ),
            ],
        ).run()


class TestPositionAdvance:
    def test_row_index_increments_and_wraps_at_pattern_end(self) -> None:
        rows_per_pattern = make_controller().project.song.rows_per_pattern

        def assert_at_row_0_order_0(context: SynthesizerContext) -> None:
            assert context.synthesizer.row_index == 0
            assert context.synthesizer.order_position == 0

        def render_all_rows_in_pattern(context: SynthesizerContext) -> None:
            for _ in range(rows_per_pattern):
                context.chunks.append(_render(context))

        def assert_wrapped_to_order_1(context: SynthesizerContext) -> None:
            assert context.synthesizer.order_position == 1
            assert context.synthesizer.row_index == 0

        BaseTestScenario(
            label="row index wraps and order position increments",
            build=_make_context,
            steps=[
                ScenarioStep(label="assert starts at order=0 row=0", action=assert_at_row_0_order_0),
                ScenarioStep(label="render all rows in pattern", action=render_all_rows_in_pattern),
                ScenarioStep(label="assert order=1 row=0", action=assert_wrapped_to_order_1),
            ],
        ).run()

    def test_shrinking_rows_below_playhead_resumes_at_next_frame(self) -> None:
        def append_second_frame(context: SynthesizerContext) -> None:
            _controller(context).project.song.append_frame()

        def seek_past_then_shrink_pattern(context: SynthesizerContext) -> None:
            context.synthesizer.set_position(0, 50)
            _controller(context).set_rows_per_pattern(16)

        def render_and_assert_advanced_without_finishing(context: SynthesizerContext) -> None:
            _, (order_position, row_index) = context.synthesizer.render_row()
            assert (order_position, row_index) == (1, 0)
            assert not context.synthesizer.is_finished

        BaseTestScenario(
            label="shrinking rows below the playhead resumes at the next frame",
            build=_make_context,
            steps=[
                ScenarioStep(label="append a second order frame", action=append_second_frame),
                ScenarioStep(
                    label="seek to row 50, then shrink pattern to 16 rows", action=seek_past_then_shrink_pattern
                ),
                ScenarioStep(
                    label="render — playhead lands on order 1 row 0, still playing",
                    action=render_and_assert_advanced_without_finishing,
                ),
            ],
        ).run()

    def test_returned_position_is_before_advance(self) -> None:
        def render_and_check_returned_position(context: SynthesizerContext) -> None:
            _, (order_position, row_index) = context.synthesizer.render_row()
            assert order_position == 0
            assert row_index == 0
            assert context.synthesizer.row_index == 1

        BaseTestScenario(
            label="render_row returns pre-advance position",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="render row 0 — returned position is 0,0", action=render_and_check_returned_position
                ),
            ],
        ).run()


class TestLoopBehavior:
    def test_loop_true_keeps_playing_after_instruction_list_exhausted(self) -> None:
        def place_two_instruction_loop_sample(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=2)
            sample = add_sample(_controller(context), recon, loop=True)
            place_row(_controller(context), generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)

        def render_row_0_and_assert_non_silence(context: SynthesizerContext) -> None:
            audio = _render(context)
            assert not np.all(audio == 0.0)

        def render_rows_1_to_3_and_assert_tick_advanced(context: SynthesizerContext) -> None:
            for _ in range(3):
                _render(context)
            assert _state(context).tick_index > 2

        BaseTestScenario(
            label="loop=True wraps instruction index",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place 2-instruction looping sample on row 0", action=place_two_instruction_loop_sample
                ),
                ScenarioStep(label="render row 0 — has audio", action=render_row_0_and_assert_non_silence),
                ScenarioStep(
                    label="render rows 1-3 — tick keeps advancing past 2",
                    action=render_rows_1_to_3_and_assert_tick_advanced,
                ),
            ],
        ).run()

    def test_loop_false_produces_silence_after_instructions_end(self) -> None:
        settings = make_controller().project.settings
        frame_length = settings.sample_rate // settings.nes_frequency

        def place_one_instruction_non_loop_sample(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=1)
            sample = add_sample(_controller(context), recon, loop=False)
            place_row(_controller(context), generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)

        def render_row_0_and_assert_first_tick_audible_rest_silent(context: SynthesizerContext) -> None:
            audio = _render(context)
            first_tick = audio[:frame_length]
            remaining = audio[frame_length:]
            assert not np.all(first_tick == 0.0), "first tick should have audio"
            assert np.all(remaining == 0.0), "ticks after instruction exhaustion should be silent"

        BaseTestScenario(
            label="loop=False silences after instruction list exhausted",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place 1-instruction non-looping sample", action=place_one_instruction_non_loop_sample
                ),
                ScenarioStep(
                    label="render row 0 — first tick audible, rest silent",
                    action=render_row_0_and_assert_first_tick_audible_rest_silent,
                ),
            ],
        ).run()


class TestSilenceCases:
    def test_none_order_slot_produces_silence(self) -> None:
        def clear_all_order_slots(context: SynthesizerContext) -> None:
            song = _controller(context).project.song
            for generator_name in GeneratorName.items():
                song.set_order_entry(0, generator_name, None)

        def render_and_assert_silence(context: SynthesizerContext) -> None:
            audio = _render(context)
            assert np.all(audio == 0.0)

        BaseTestScenario(
            label="None order slot produces silence",
            build=_make_context,
            steps=[
                ScenarioStep(label="set all order slots to None", action=clear_all_order_slots),
                ScenarioStep(label="render row — silence", action=render_and_assert_silence),
            ],
        ).run()

    def test_finished_synthesizer_returns_silence(self) -> None:
        total_rows = make_controller().project.song.rows_per_pattern

        def exhaust_song(context: SynthesizerContext) -> None:
            for _ in range(total_rows):
                _render(context)

        def assert_finished(context: SynthesizerContext) -> None:
            assert context.synthesizer.is_finished

        def render_beyond_end_and_assert_silence(context: SynthesizerContext) -> None:
            audio = _render(context)
            assert np.all(audio == 0.0)

        BaseTestScenario(
            label="finished synthesizer returns silence",
            build=_make_context,
            steps=[
                ScenarioStep(label="exhaust all rows", action=exhaust_song),
                ScenarioStep(label="assert is_finished", action=assert_finished),
                ScenarioStep(label="render past end — silence", action=render_beyond_end_and_assert_silence),
            ],
        ).run()


class TestFrameCount:
    def test_chunk_length_matches_speed_sample_rate_and_nes_frequency(self) -> None:
        def render_and_assert_chunk_length(context: SynthesizerContext) -> None:
            settings = _controller(context).project.settings
            frame_length = settings.sample_rate // settings.nes_frequency
            ticks_per_row = (settings.speed * settings.nes_frequency * REFERENCE_TEMPO) // (
                settings.tempo * REFERENCE_NES_FREQUENCY
            )
            audio = _render(context)
            assert len(audio) == frame_length * ticks_per_row

        BaseTestScenario(
            label="chunk length matches timing formula",
            build=_make_context,
            steps=[
                ScenarioStep(label="render one row and check length", action=render_and_assert_chunk_length),
            ],
        ).run()


class TestNesFrequencyTempo:
    def test_frame_length_follows_project_nes_frequency(self) -> None:
        """Each tick spans ``sample_rate / nes_frequency`` samples taken from the project's
        live frequency, not the fixed library config — otherwise the row duration drifts."""

        def lower_nes_frequency(context: SynthesizerContext) -> None:
            _controller(context).set_nes_frequency(30)

        def render_and_assert_chunk_uses_project_frequency(context: SynthesizerContext) -> None:
            settings = _controller(context).project.settings
            frame_length = round(settings.sample_rate / settings.nes_frequency)
            ticks_per_row = (settings.speed * settings.nes_frequency * REFERENCE_TEMPO) // (
                settings.tempo * REFERENCE_NES_FREQUENCY
            )
            audio = _render(context)
            assert len(audio) == frame_length * ticks_per_row

        BaseTestScenario(
            label="frame length tracks the project NES frequency",
            build=_make_context,
            steps=[
                ScenarioStep(label="lower NES frequency to 30", action=lower_nes_frequency),
                ScenarioStep(
                    label="render — chunk uses project frequency",
                    action=render_and_assert_chunk_uses_project_frequency,
                ),
            ],
        ).run()

    def test_tempo_is_independent_of_nes_frequency(self) -> None:
        """A whole pattern spans the same real time at 60 Hz and 30 Hz; only the instruction
        rate differs. Before the fix, halving the frequency roughly doubled the tempo."""

        def pattern_duration_seconds(nes_frequency: int) -> float:
            controller = make_controller()
            controller.set_nes_frequency(nes_frequency)
            synthesizer = RowSynthesizer(controller, Config())
            rows = controller.project.song.rows_per_pattern
            total_samples = sum(len(synthesizer.render_row()[0]) for _ in range(rows))
            return total_samples / controller.project.settings.sample_rate

        assert abs(pattern_duration_seconds(60) - pattern_duration_seconds(30)) < 0.1

    def test_frequency_change_between_rows_takes_effect_without_restart(self) -> None:
        """A frequency change mid-playback is picked up on the next row: render_row reads the
        live setting and rebuilds the generators in place, keeping the sounding note going."""
        controller = make_controller()
        recon = make_pulse_reconstruction(count=12)
        sample = add_sample(controller, recon)
        place_row(controller, generator=GeneratorName.PULSE1, row_index=0, sample_id=sample.id)
        synthesizer = RowSynthesizer(controller, Config())
        sample_rate = controller.project.settings.sample_rate
        pulse_state = synthesizer._channel_states[GeneratorName.PULSE1]

        synthesizer.render_row()
        assert pulse_state.generator.frame_length == round(sample_rate / 60)

        controller.set_nes_frequency(30)
        synthesizer.render_row()

        assert pulse_state.generator.frame_length == round(sample_rate / 30)
        assert pulse_state.sample_id is not None
