from dataclasses import dataclass, field
from typing import Dict, Final, FrozenSet, List, Optional, Tuple

import numpy as np
import pytest

from sampletones_application.constants.playback import (
    MAX_TICKS_PER_ROW,
    MIN_TICKS_PER_ROW,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.channels import ALL_CHANNELS
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_core.configs import Config
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.timing import Metre, RowRate, calculate_groove
from tests.suite.scenario import BaseTestScenario, ScenarioStep
from tests.unit.sampletones_application.logic.sequencer.playback.conftest import (
    add_sample,
    make_controller,
    make_pulse_reconstruction,
    make_synthesizer,
    place_modifier_row,
    place_note_off,
    place_row,
)

SAMPLE_RATE: Final[int] = DEFAULT_SAMPLE_RATE
SUSTAINED_FRAMES: Final[int] = 64
QUIET_VOLUME: Final[int] = 3


class MaskProvider:
    """A channel mask a test moves between rows, standing in for the channels logic."""

    __test__ = False

    def __init__(self) -> None:
        self.active: FrozenSet[ChannelName] = ALL_CHANNELS

    def mute(self, channel: ChannelName) -> None:
        self.active = ALL_CHANNELS - {channel}

    def __call__(self) -> FrozenSet[ChannelName]:
        return self.active


@dataclass
class SynthesizerContext:
    synthesizer: RowSynthesizer
    controller: ProjectController
    mask: MaskProvider
    chunks: List[np.ndarray] = field(default_factory=list)
    tick_snapshots: Dict[str, int] = field(default_factory=dict)
    sample_id_snapshots: Dict[str, Optional[str]] = field(default_factory=dict)


def _make_context() -> SynthesizerContext:
    controller = make_controller()
    mask = MaskProvider()
    return SynthesizerContext(
        synthesizer=make_synthesizer(controller, Config(), active_channels=mask),
        controller=controller,
        mask=mask,
    )


def _controller(context: SynthesizerContext) -> ProjectController:
    return context.controller


def _state(
    context: SynthesizerContext,
    channel: ChannelName = ChannelName.PULSE1,
):
    return context.synthesizer._channels.state(channel)


def _render(context: SynthesizerContext) -> np.ndarray:
    audio, _ = context.synthesizer.render_row()
    context.chunks.append(audio)
    return audio


def _groove_ticks(controller: ProjectController) -> Tuple[int, ...]:
    """The ticks each row of a pattern owes the project's timing, from the timing package itself."""
    settings = controller.project.settings
    return calculate_groove(
        RowRate.from_settings(settings),
        Metre.from_settings(settings, rows=controller.project.song.rows_per_pattern),
        minimum_ticks=MIN_TICKS_PER_ROW,
        maximum_ticks=MAX_TICKS_PER_ROW,
    ).ticks


def _row_ticks(
    synthesizer: RowSynthesizer,
    rows: int,
) -> Tuple[int, ...]:
    """The ticks ``rows`` consecutive rendered rows last, read back from the audio they produced."""
    settings = synthesizer._project_source.project.settings
    frame_length = round(settings.sample_rate / settings.nes_frequency)
    return tuple(len(synthesizer.render_row()[0]) // frame_length for _ in range(rows))


class TestTriggerSetsDefaults:
    def test_transpose_and_volume_default_to_zero_and_max(self) -> None:
        def place_pulse_sample_on_row_0(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(pitch=60, volume=15, count=4)
            sample = add_sample(_controller(context), recon)
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )

        def render_row_0_and_assert_defaults(context: SynthesizerContext) -> None:
            _render(context)
            assert _state(context).transpose == 0
            assert _state(context).volume == MAX_VOLUME

        BaseTestScenario(
            label="trigger sets default transpose and volume",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place pulse sample on row 0",
                    action=place_pulse_sample_on_row_0,
                ),
                ScenarioStep(
                    label="render row 0 — assert defaults",
                    action=render_row_0_and_assert_defaults,
                ),
            ],
        ).run()

    def test_explicit_transpose_and_volume_from_row(self) -> None:
        def place_pulse_sample_with_modifiers(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=4)
            sample = add_sample(_controller(context), recon)
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
                transpose=5,
                volume=8,
            )

        def render_row_0_and_assert_explicit_values(
            context: SynthesizerContext,
        ) -> None:
            _render(context)
            assert _state(context).transpose == 5
            assert _state(context).volume == 8

        BaseTestScenario(
            label="trigger with explicit modifiers",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place pulse sample with transpose=5 volume=8",
                    action=place_pulse_sample_with_modifiers,
                ),
                ScenarioStep(
                    label="render row 0 — assert explicit values",
                    action=render_row_0_and_assert_explicit_values,
                ),
            ],
        ).run()


class TestSustain:
    def test_empty_row_continues_previous_note(self) -> None:
        def place_pulse_sample_on_row_0(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=12)
            sample = add_sample(_controller(context), recon)
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )

        def render_row_0_and_record_state(context: SynthesizerContext) -> None:
            _render(context)
            context.tick_snapshots["after_row_0"] = _state(context).tick_index
            context.sample_id_snapshots["triggered"] = _state(context).sample_id
            assert _state(context).sample_id is not None

        def render_empty_row_1_and_assert_tick_advanced(
            context: SynthesizerContext,
        ) -> None:
            _render(context)
            assert _state(context).tick_index > context.tick_snapshots["after_row_0"]
            assert _state(context).sample_id == context.sample_id_snapshots["triggered"]

        BaseTestScenario(
            label="sustain — empty row continues previous note",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place pulse sample on row 0",
                    action=place_pulse_sample_on_row_0,
                ),
                ScenarioStep(
                    label="render row 0 — note triggers",
                    action=render_row_0_and_record_state,
                ),
                ScenarioStep(
                    label="render row 1 (empty) — note sustains",
                    action=render_empty_row_1_and_assert_tick_advanced,
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
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
                volume=15,
            )
            place_modifier_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=1,
                volume=0,
            )

        def render_row_0_and_record_state(context: SynthesizerContext) -> None:
            _render(context)
            context.tick_snapshots["after_row_0"] = _state(context).tick_index
            context.sample_id_snapshots["after_row_0"] = _state(context).sample_id
            assert _state(context).volume == 15

        def render_modifier_row_and_assert_volume_changed(
            context: SynthesizerContext,
        ) -> None:
            _render(context)
            assert _state(context).volume == 0
            assert _state(context).sample_id == context.sample_id_snapshots["after_row_0"]
            assert _state(context).tick_index > context.tick_snapshots["after_row_0"]

        BaseTestScenario(
            label="modifier-only row changes volume without retriggering",
            build=_make_context,
            steps=[
                ScenarioStep(label="place sample on row 0, modifier on row 1", action=setup),
                ScenarioStep(
                    label="render row 0 — volume=15",
                    action=render_row_0_and_record_state,
                ),
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
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
                transpose=0,
            )
            place_modifier_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=1,
                transpose=7,
            )

        def render_row_0_and_record_sample(context: SynthesizerContext) -> None:
            _render(context)
            context.sample_id_snapshots["triggered"] = _state(context).sample_id
            assert _state(context).transpose == 0

        def render_modifier_row_and_assert_transpose_changed(
            context: SynthesizerContext,
        ) -> None:
            _render(context)
            assert _state(context).transpose == 7
            assert _state(context).sample_id == context.sample_id_snapshots["triggered"]

        BaseTestScenario(
            label="modifier-only row changes transpose without retriggering",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place sample on row 0, transpose modifier on row 1",
                    action=setup,
                ),
                ScenarioStep(
                    label="render row 0 — transpose=0",
                    action=render_row_0_and_record_sample,
                ),
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
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )

        def mute_pulse1(context: SynthesizerContext) -> None:
            context.mask.mute(ChannelName.PULSE1)

        def render_and_compare_against_unmasked(context: SynthesizerContext) -> None:
            audio_masked = _render(context)

            audible_synthesizer = make_synthesizer(_controller(context), Config())
            audio_with_pulse1, _ = audible_synthesizer.render_row()

            assert np.allclose(audio_masked, 0.0)
            assert not np.allclose(audio_with_pulse1, 0.0)

        BaseTestScenario(
            label="masked channel excluded from mix",
            build=_make_context,
            steps=[
                ScenarioStep(label="place pulse sample on row 0", action=place_pulse_sample),
                ScenarioStep(label="mask out PULSE1", action=mute_pulse1),
                ScenarioStep(
                    label="render and assert silence while the audible mix sounds",
                    action=render_and_compare_against_unmasked,
                ),
            ],
        ).run()

    def test_mask_change_between_rows_takes_effect_without_restart(self) -> None:
        """The mask is read per row, so unmuting mid-song is heard on the next row rendered.

        The sustained note keeps its state through the muted row, so the channel resumes at the
        pitch and volume the pattern has reached rather than retriggering.
        """

        def place_looping_pulse_sample(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=4)
            sample = add_sample(_controller(context), recon, loop=True)
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )

        def mute_pulse1_and_render_row_0(context: SynthesizerContext) -> None:
            context.mask.mute(ChannelName.PULSE1)
            assert np.allclose(_render(context), 0.0)
            assert _state(context).sample_id is not None

        def unmute_pulse1_and_render_row_1(context: SynthesizerContext) -> None:
            context.mask.active = ALL_CHANNELS
            assert not np.allclose(_render(context), 0.0)

        BaseTestScenario(
            label="mask change heard on the next row",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place looping pulse sample on row 0",
                    action=place_looping_pulse_sample,
                ),
                ScenarioStep(
                    label="mute PULSE1, render row 0 — silence",
                    action=mute_pulse1_and_render_row_0,
                ),
                ScenarioStep(
                    label="unmute PULSE1, render row 1 — sounds",
                    action=unmute_pulse1_and_render_row_1,
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
                ScenarioStep(
                    label="assert starts at order=0 row=0",
                    action=assert_at_row_0_order_0,
                ),
                ScenarioStep(
                    label="render all rows in pattern",
                    action=render_all_rows_in_pattern,
                ),
                ScenarioStep(label="assert order=1 row=0", action=assert_wrapped_to_order_1),
            ],
        ).run()

    def test_shrinking_rows_below_playhead_resumes_at_next_frame(self) -> None:
        def append_second_frame(context: SynthesizerContext) -> None:
            _controller(context).project.song.append_frame()

        def seek_past_then_shrink_pattern(context: SynthesizerContext) -> None:
            context.synthesizer.set_position(0, 50)
            _controller(context).set_rows_per_pattern(16)

        def render_and_assert_advanced_without_finishing(
            context: SynthesizerContext,
        ) -> None:
            _, (order_position, row_index) = context.synthesizer.render_row()
            assert (order_position, row_index) == (1, 0)
            assert not context.synthesizer.is_finished

        BaseTestScenario(
            label="shrinking rows below the playhead resumes at the next frame",
            build=_make_context,
            steps=[
                ScenarioStep(label="append a second order frame", action=append_second_frame),
                ScenarioStep(
                    label="seek to row 50, then shrink pattern to 16 rows",
                    action=seek_past_then_shrink_pattern,
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
                    label="render row 0 — returned position is 0,0",
                    action=render_and_check_returned_position,
                ),
            ],
        ).run()


class TestNoteOff:
    def test_note_off_cuts_a_sounding_looped_voice(self) -> None:
        def place_looped_sample_then_note_off(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=2)
            sample = add_sample(_controller(context), recon, loop=True)
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )
            place_note_off(_controller(context), channel=ChannelName.PULSE1, row_index=1)

        def render_row_0_and_assert_audible(context: SynthesizerContext) -> None:
            assert not np.all(_render(context) == 0.0)

        def render_row_1_and_assert_silenced(context: SynthesizerContext) -> None:
            audio = _render(context)
            assert np.all(audio == 0.0)
            assert _state(context).sample_id is None

        BaseTestScenario(
            label="note-off silences a looped voice and clears channel state",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place looped sample on row 0, note-off on row 1",
                    action=place_looped_sample_then_note_off,
                ),
                ScenarioStep(
                    label="render row 0 — audible",
                    action=render_row_0_and_assert_audible,
                ),
                ScenarioStep(
                    label="render row 1 — note-off cuts the voice",
                    action=render_row_1_and_assert_silenced,
                ),
            ],
        ).run()


class TestLoopBehavior:
    def test_loop_true_keeps_playing_after_instruction_list_exhausted(self) -> None:
        def place_two_instruction_loop_sample(context: SynthesizerContext) -> None:
            recon = make_pulse_reconstruction(count=2)
            sample = add_sample(_controller(context), recon, loop=True)
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )

        def render_row_0_and_assert_non_silence(context: SynthesizerContext) -> None:
            audio = _render(context)
            assert not np.all(audio == 0.0)

        def render_rows_1_to_3_and_assert_tick_advanced(
            context: SynthesizerContext,
        ) -> None:
            for _ in range(3):
                _render(context)
            assert _state(context).tick_index > 2

        BaseTestScenario(
            label="loop=True wraps instruction index",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="place 2-instruction looping sample on row 0",
                    action=place_two_instruction_loop_sample,
                ),
                ScenarioStep(
                    label="render row 0 — has audio",
                    action=render_row_0_and_assert_non_silence,
                ),
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
            place_row(
                _controller(context),
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )

        def render_row_0_and_assert_first_tick_audible_rest_silent(
            context: SynthesizerContext,
        ) -> None:
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
                    label="place 1-instruction non-looping sample",
                    action=place_one_instruction_non_loop_sample,
                ),
                ScenarioStep(
                    label="render row 0 — first tick audible, rest silent",
                    action=render_row_0_and_assert_first_tick_audible_rest_silent,
                ),
            ],
        ).run()

    def test_looped_voice_sustains_across_an_empty_next_frame(self) -> None:
        def place_loop_then_append_empty_frame(context: SynthesizerContext) -> None:
            controller = _controller(context)
            recon = make_pulse_reconstruction(count=2)
            sample = add_sample(controller, recon, loop=True)
            place_row(
                controller,
                channel=ChannelName.PULSE1,
                row_index=0,
                sample_id=sample.id,
            )
            controller.append_frame()

        def render_into_empty_second_frame_and_assert_sustained(
            context: SynthesizerContext,
        ) -> None:
            rows_in_first_frame = _controller(context).project.song.rows_per_pattern
            for _ in range(rows_in_first_frame):
                _render(context)

            audio, (order_position, _) = context.synthesizer.render_row()
            assert order_position == 1
            assert not np.all(audio == 0.0)
            assert _state(context).sample_id is not None

        BaseTestScenario(
            label="looped voice carries across an empty (None-slot) next frame",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="loop on frame 0, append all-None frame 1",
                    action=place_loop_then_append_empty_frame,
                ),
                ScenarioStep(
                    label="render into frame 1 — voice still sounding",
                    action=render_into_empty_second_frame_and_assert_sustained,
                ),
            ],
        ).run()


class TestSilenceCases:
    def test_none_order_slot_with_no_sounding_voice_produces_silence(self) -> None:
        def clear_all_order_slots(context: SynthesizerContext) -> None:
            song = _controller(context).project.song
            for channel_name in ChannelName.items():
                song.set_order_entry(0, channel_name, None)

        def render_and_assert_silence(context: SynthesizerContext) -> None:
            audio = _render(context)
            assert np.all(audio == 0.0)

        BaseTestScenario(
            label="None order slot with nothing sounding produces silence",
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
                ScenarioStep(
                    label="render past end — silence",
                    action=render_beyond_end_and_assert_silence,
                ),
            ],
        ).run()


class TestFrameCount:
    def test_chunk_length_matches_the_groove_row_and_the_frame_length(self) -> None:
        def render_and_assert_chunk_length(context: SynthesizerContext) -> None:
            controller = _controller(context)
            settings = controller.project.settings
            frame_length = settings.sample_rate // settings.nes_frequency
            audio = _render(context)
            assert len(audio) == frame_length * _groove_ticks(controller)[0]

        BaseTestScenario(
            label="chunk length matches the groove's first row",
            build=_make_context,
            steps=[
                ScenarioStep(
                    label="render one row and check length",
                    action=render_and_assert_chunk_length,
                ),
            ],
        ).run()


class TestGroove:
    def test_a_pattern_plays_the_groove_the_metre_yields(
        self,
        controller: ProjectController,
        synthesizer: RowSynthesizer,
    ) -> None:
        """Speed 6 at 60 Hz against tempo 210 asks for 30/7 ticks a row, which no single speed
        value states. Spread over a 16-row bar of four-row beats it comes out as the bar, its
        half, and each beat carrying the longer row.
        """
        controller.set_rows_per_pattern(16)
        controller.set_tempo(210)

        rendered = _row_ticks(synthesizer, controller.project.song.rows_per_pattern)

        assert rendered == (5, 4, 5, 4, 5, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4)
        assert rendered == _groove_ticks(controller)

    def test_the_groove_restarts_with_the_pattern(
        self,
        controller: ProjectController,
        synthesizer: RowSynthesizer,
    ) -> None:
        """Every row reads the groove entry its position in the pattern names, so returning to
        row 0 plays row 0's duration again — the phase an exported module also restarts on.
        """
        controller.set_rows_per_pattern(16)
        controller.set_tempo(210)

        opening = _row_ticks(synthesizer, 3)
        synthesizer.set_position(0, 0)
        again = _row_ticks(synthesizer, 1)

        assert opening == (5, 4, 5)
        assert again == (opening[0],)

    def test_tempo_change_between_rows_rebuilds_the_groove(
        self,
        controller: ProjectController,
        synthesizer: RowSynthesizer,
    ) -> None:
        """A tempo edit is heard on the next row, at that row's place in the new groove."""
        controller.set_rows_per_pattern(16)
        speed = controller.project.settings.speed

        at_reference_tempo = _row_ticks(synthesizer, 1)
        controller.set_tempo(210)
        after_change = _row_ticks(synthesizer, 1)

        assert at_reference_tempo == (speed,)
        assert after_change == (_groove_ticks(controller)[1],)

    def test_highlight_change_regroups_the_same_row_rate(
        self,
        controller: ProjectController,
        synthesizer: RowSynthesizer,
    ) -> None:
        """The beat decides where the longer rows land, so narrowing it moves them without
        changing how long the pattern lasts.
        """
        controller.set_rows_per_pattern(16)
        controller.set_tempo(210)
        rows = controller.project.song.rows_per_pattern

        on_four_row_beats = _row_ticks(synthesizer, rows)
        controller.set_first_highlight(3)
        synthesizer.set_position(0, 0)
        on_three_row_beats = _row_ticks(synthesizer, rows)

        assert on_three_row_beats == (5, 4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 4)
        assert sum(on_three_row_beats) == sum(on_four_row_beats)


class TestNesFrequencyTempo:
    def test_frame_length_follows_project_nes_frequency(self) -> None:
        """Each tick spans ``sample_rate / nes_frequency`` samples taken from the project's
        live frequency, not the fixed library config — otherwise the row duration drifts.
        """

        def lower_nes_frequency(context: SynthesizerContext) -> None:
            _controller(context).set_nes_frequency(30)

        def render_and_assert_chunk_uses_project_frequency(
            context: SynthesizerContext,
        ) -> None:
            controller = _controller(context)
            settings = controller.project.settings
            frame_length = round(settings.sample_rate / settings.nes_frequency)
            audio = _render(context)
            assert len(audio) == frame_length * _groove_ticks(controller)[0]

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
        rate differs. Before the fix, halving the frequency roughly doubled the tempo.
        """

        def pattern_duration_seconds(nes_frequency: int) -> float:
            controller = make_controller()
            controller.set_nes_frequency(nes_frequency)
            synthesizer = make_synthesizer(controller, Config(), sample_rate=SAMPLE_RATE)
            rows = controller.project.song.rows_per_pattern
            total_samples = sum(len(synthesizer.render_row()[0]) for _ in range(rows))
            return total_samples / SAMPLE_RATE

        assert abs(pattern_duration_seconds(60) - pattern_duration_seconds(30)) < 0.1

    def test_frequency_change_between_rows_takes_effect_without_restart(self) -> None:
        """A frequency change mid-playback is picked up on the next row: render_row reads the
        live setting and rebuilds the generators in place, keeping the sounding note going.
        """
        controller = make_controller()
        recon = make_pulse_reconstruction(count=12)
        sample = add_sample(controller, recon)
        place_row(controller, channel=ChannelName.PULSE1, row_index=0, sample_id=sample.id)
        synthesizer = make_synthesizer(controller, Config(), sample_rate=SAMPLE_RATE)

        controller.set_nes_frequency(60)
        synthesizer.render_row()
        pulse_state = synthesizer._channels.state(ChannelName.PULSE1)
        assert pulse_state.generator.frame_length == round(SAMPLE_RATE / 60)

        controller.set_nes_frequency(30)
        synthesizer.render_row()

        assert pulse_state.generator.frame_length == round(SAMPLE_RATE / 30)
        assert pulse_state.sample_id is not None


class TestChannelHeldValues:
    """A dimension an instrument leaves to the channel sounds at the value the channel holds.

    The channel carries that value from the start of a song, taking up a new one wherever an
    instrument writes it, so an instrument with an empty volume envelope plays at whatever the
    one before it left behind.
    """

    @staticmethod
    def _place(
        context: SynthesizerContext,
        reconstruction: Reconstruction,
        *,
        row_index: int,
        name: str,
    ) -> None:
        sample = add_sample(_controller(context), reconstruction, name=name)
        place_row(
            _controller(context),
            channel=ChannelName.PULSE1,
            row_index=row_index,
            sample_id=sample.id,
        )

    @staticmethod
    def _peak(audio: np.ndarray) -> float:
        return float(np.max(np.abs(audio)))

    def test_the_channel_takes_up_the_level_its_instrument_writes(self) -> None:
        context = _make_context()
        self._place(
            context,
            make_pulse_reconstruction(volume=QUIET_VOLUME, count=SUSTAINED_FRAMES),
            row_index=0,
            name="writes",
        )

        _render(context)

        assert _state(context).feature_values[FeatureKey.VOLUME] == QUIET_VOLUME

    def test_a_sample_holding_its_level_sounds_at_the_channels(self) -> None:
        context = _make_context()
        self._place(
            context,
            make_pulse_reconstruction(volume=QUIET_VOLUME, count=SUSTAINED_FRAMES),
            row_index=0,
            name="writes",
        )
        self._place(
            context,
            make_pulse_reconstruction(
                volume=MAX_VOLUME,
                count=SUSTAINED_FRAMES,
                held_features=(FeatureKey.VOLUME,),
            ),
            row_index=1,
            name="holds",
        )

        written = _render(context)
        held = _render(context)

        assert self._peak(held) == pytest.approx(self._peak(written))

    def test_a_song_starts_a_held_level_at_full_volume(self) -> None:
        holding = _make_context()
        self._place(
            holding,
            make_pulse_reconstruction(
                volume=QUIET_VOLUME,
                count=SUSTAINED_FRAMES,
                held_features=(FeatureKey.VOLUME,),
            ),
            row_index=0,
            name="holds",
        )
        writing = _make_context()
        self._place(
            writing,
            make_pulse_reconstruction(volume=MAX_VOLUME, count=SUSTAINED_FRAMES),
            row_index=0,
            name="writes",
        )

        assert self._peak(_render(holding)) == pytest.approx(self._peak(_render(writing)))

    def test_a_reset_returns_every_channel_to_the_values_a_song_starts_on(self) -> None:
        context = _make_context()
        self._place(
            context,
            make_pulse_reconstruction(volume=QUIET_VOLUME, count=SUSTAINED_FRAMES),
            row_index=0,
            name="writes",
        )
        _render(context)

        context.synthesizer.reset()

        assert _state(context).feature_values == CHANNEL_FEATURE_DEFAULTS
