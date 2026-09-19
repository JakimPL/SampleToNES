from pathlib import Path
from typing import Dict, Final, List, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ALL_CHANNELS, ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.builder import streams_from_instructions
from sampletones_player.compression.absent import is_absent
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import TonePlanes
from sampletones_player.compression.planes.separate import channel_planes, planes_from_streams
from sampletones_player.compression.seeds import phrases_from_project
from sampletones_player.registers.channel import channel_registers
from sampletones_player.specification.binary import unsigned_byte
from sampletones_shared.music import Tuning
from sampletones_tools.codec.study.corpus.notes import channel_notes, song_notes
from sampletones_tools.codec.study.corpus.slices import project_slices
from sampletones_tools.codec.study.corpus.song import SongGroup, StudySong
from sampletones_tools.codec.study.layouts.encode import encode_layout
from sampletones_tools.codec.study.layouts.layout import Anchor, BendForm, PlaneLayout
from sampletones_tools.codec.study.layouts.planes import layout_planes, layout_seeds
from sampletones_tools.codec.study.layouts.tone import FLAG_BIT, tone_planes
from tests.suite.performance import project_with_instrument
from tests.suite.player import PLAYER_FULL_VOLUME, PLAYER_REFERENCE_PITCH
from tests.suite.study import NO_STUDY_SLICES

TUNING: Final[Tuning] = Tuning()
PITCHES: Final[PitchTable] = PitchTable.from_tuning(TUNING)
TIMER_TABLE: Final[Dict[int, int]] = get_timer_table(TUNING)
LOW_PITCH: Final[int] = PLAYER_REFERENCE_PITCH - 12
PAST_HALFWAY: Final[int] = -20
BEYOND_A_BYTE: Final[int] = 10
ROWS_PER_PATTERN: Final[int] = 8

NEAREST_DENSE: Final[PlaneLayout] = PlaneLayout(Anchor.NEAREST, BendForm.DENSE)
NAMED_DENSE: Final[PlaneLayout] = PlaneLayout(Anchor.NAMED, BendForm.DENSE)
EVERY_LAYOUT: Final[Tuple[PlaneLayout, ...]] = tuple(
    PlaneLayout(anchor, form) for anchor in Anchor for form in BendForm
)


def bent_frames(pitch: int, bends: Sequence[int]) -> List[InstructionUnion]:
    return [
        PulseInstruction(on=True, pitch=pitch, volume=PLAYER_FULL_VOLUME, duty_cycle=0, detune=bend) for bend in bends
    ]


def coarse_frame(pitch: int, coarse: int) -> List[InstructionUnion]:
    return [PulseInstruction(on=True, pitch=pitch, volume=PLAYER_FULL_VOLUME, duty_cycle=0, coarse_detune=coarse)]


def pulse_planes(instructions: Sequence[InstructionUnion]) -> TonePlanes:
    registers = channel_registers(ChannelName.PULSE1, {ChannelName.PULSE1: instructions}, TIMER_TABLE)
    planes = channel_planes(ChannelName.PULSE1, registers, PITCHES)
    assert isinstance(planes, TonePlanes)
    return planes


def written(instructions: Sequence[InstructionUnion], layout: PlaneLayout) -> Tuple[bytes, bytes, bytes]:
    return tone_planes(
        pulse_planes(instructions),
        channel_notes(ChannelName.PULSE1, instructions),
        PITCHES,
        layout,
    )


def study_song(instructions: Sequence[InstructionUnion]) -> StudySong:
    played = {ChannelName.PULSE1: instructions}
    streams = streams_from_instructions(played, TIMER_TABLE)
    return StudySong(
        name="bent",
        group=SongGroup.RECONSTRUCTION,
        source=Path("bent.stn"),
        planes=planes_from_streams(streams, PITCHES),
        seeds=(),
        pitches=PITCHES,
        notes=song_notes(played, streams.ticks),
        slices=NO_STUDY_SLICES,
    )


class TestTheNotesATickNames:
    """The notes line up with the ticks a tone channel's registers cover."""

    def test_the_notes_cover_the_registers_ticks(self) -> None:
        instructions = bent_frames(PLAYER_REFERENCE_PITCH, (0, 3))
        registers = channel_registers(ChannelName.PULSE1, {ChannelName.PULSE1: instructions}, TIMER_TABLE)
        assert channel_notes(ChannelName.PULSE1, instructions) == bytes((PLAYER_REFERENCE_PITCH,)) * len(registers)

    def test_a_rest_holds_the_note_last_sounded(self) -> None:
        instructions = [*bent_frames(LOW_PITCH, (0,)), PulseInstruction.null_instruction()]
        assert channel_notes(ChannelName.PULSE1, instructions) == bytes((LOW_PITCH, LOW_PITCH))

    def test_a_channel_running_out_holds_its_note_through_the_song(self) -> None:
        notes = song_notes({ChannelName.PULSE1: bent_frames(LOW_PITCH, (0,))}, 4)
        assert notes[0] == bytes((LOW_PITCH,)) * 4

    def test_the_noise_channel_names_no_note(self) -> None:
        with pytest.raises(ValueError):
            channel_notes(ChannelName.NOISE, [])


class TestWhatTheValuePlaneNames:
    def test_the_nearest_dense_layout_is_the_production_separation(self) -> None:
        instructions = bent_frames(PLAYER_REFERENCE_PITCH, (0, 5, PAST_HALFWAY, -5))
        planes = pulse_planes(instructions)
        assert written(instructions, NEAREST_DENSE) == planes.ordered

    def test_a_named_note_keeps_a_bend_past_halfway(self) -> None:
        instructions = bent_frames(PLAYER_REFERENCE_PITCH, (PAST_HALFWAY,))
        _, value, bend = written(instructions, NAMED_DENSE)
        _, nearest, _ = written(instructions, NEAREST_DENSE)
        assert PITCHES.timers[value[0]] == TIMER_TABLE[PLAYER_REFERENCE_PITCH]
        assert bend[0] == unsigned_byte(PAST_HALFWAY)
        assert nearest[0] != value[0]

    def test_a_bend_beyond_a_byte_falls_back_to_the_nearest_pitch(self) -> None:
        instructions = coarse_frame(PLAYER_REFERENCE_PITCH, BEYOND_A_BYTE)
        assert written(instructions, NAMED_DENSE) == written(instructions, NEAREST_DENSE)

    def test_a_named_bend_survives_a_transposition_byte_for_byte(self) -> None:
        """The song walk moves a transposed note and keeps its bend in divider steps."""
        bends = (0, PAST_HALFWAY, PAST_HALFWAY, 0)
        low = written(bent_frames(LOW_PITCH, bends), NAMED_DENSE)
        high = written(bent_frames(PLAYER_REFERENCE_PITCH, bends), NAMED_DENSE)
        assert low[2] == high[2]
        assert (
            written(bent_frames(LOW_PITCH, bends), NEAREST_DENSE)[2]
            != written(bent_frames(PLAYER_REFERENCE_PITCH, bends), NEAREST_DENSE)[2]
        )


class TestAFlaggedBendPlane:
    def test_the_flag_marks_each_bent_tick_and_the_plane_holds_those_alone(self) -> None:
        bends = (0, 3, 0, -3, 0)
        _, value, bend = written(
            bent_frames(PLAYER_REFERENCE_PITCH, bends), PlaneLayout(Anchor.NEAREST, BendForm.FLAGGED_TICKS)
        )
        assert [bool(byte & FLAG_BIT) for byte in value[: len(bends)]] == [offset != 0 for offset in bends]
        assert bend == bytes(unsigned_byte(offset) for offset in bends if offset)

    def test_a_flagged_note_spans_its_first_bend_to_its_last(self) -> None:
        bends = (0, 3, 0, -3, 0)
        _, value, bend = written(
            bent_frames(PLAYER_REFERENCE_PITCH, bends), PlaneLayout(Anchor.NEAREST, BendForm.FLAGGED_NOTES)
        )
        assert [bool(byte & FLAG_BIT) for byte in value[: len(bends)]] == [False, True, True, True, False]
        assert bend == bytes(unsigned_byte(offset) for offset in bends[1:4])

    @pytest.mark.parametrize("form", (BendForm.FLAGGED_TICKS, BendForm.FLAGGED_NOTES), ids=str)
    def test_an_unbent_channel_holds_no_bend_and_no_flag(self, form: BendForm) -> None:
        instructions = bent_frames(PLAYER_REFERENCE_PITCH, (0, 0, 0))
        _, value, bend = written(instructions, PlaneLayout(Anchor.NEAREST, form))
        assert bend == b""
        assert value == pulse_planes(instructions).value


class TestALayoutsSeeds:
    def test_the_nearest_dense_layout_seeds_what_production_seeds(self) -> None:
        instrument = Instrument(
            name="bent",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(PLAYER_FULL_VOLUME,) * 4),
                pitch=Envelope(items=(0, 4, PAST_HALFWAY, 0)),
            ),
            initial_pitch=PLAYER_REFERENCE_PITCH,
        )
        project = project_with_instrument(instrument, rows_per_pattern=ROWS_PER_PATTERN)
        slices = project_slices(project, TUNING)
        assert layout_seeds(slices, PITCHES, NEAREST_DENSE) == phrases_from_project(project, TUNING, ALL_CHANNELS)


class TestEncodingALayout:
    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=lambda layout: f"{layout.anchor}-{layout.form}")
    def test_every_layout_plays_back_what_it_wrote(self, layout: PlaneLayout) -> None:
        song = study_song(bent_frames(PLAYER_REFERENCE_PITCH, (0, 3, 6, 3, 0, PAST_HALFWAY, 0)))
        assert encode_layout(song, layout).lossless

    @pytest.mark.parametrize("layout", EVERY_LAYOUT, ids=lambda layout: f"{layout.anchor}-{layout.form}")
    def test_an_absent_plane_costs_no_stream(self, layout: PlaneLayout) -> None:
        song = study_song(bent_frames(PLAYER_REFERENCE_PITCH, (0, 3, 0)))
        planes = layout_planes(song, layout)
        streams = encode_layout(song, layout).streams
        assert any(is_absent(plane) for plane in planes)
        assert all(size == 0 for plane, size in zip(planes, streams) if is_absent(plane))
        assert all(size > 0 for plane, size in zip(planes, streams) if not is_absent(plane))
