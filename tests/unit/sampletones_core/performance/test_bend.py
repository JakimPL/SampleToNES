from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.performance import (
    ChannelPerformance,
    VoiceReading,
    apply_modifiers,
    apply_row,
    sound_tick,
)
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_on import NoteOn

REFERENCE: Final[int] = 60
SEMITONE: Final[int] = 1
BEND: Final[int] = 5
COARSE_BEND: Final[int] = 2


def _instrument(**envelopes: Envelope[int]) -> Instrument:
    return Instrument(
        name="bent",
        envelopes=InstrumentEnvelopes(volume=Envelope(items=(MAX_VOLUME, MAX_VOLUME)), **envelopes),
        initial_pitch=REFERENCE,
    )


def _played(instrument: Instrument, ticks: int) -> List[InstructionUnion]:
    """The frames one channel sounds, tick by tick, with the channel's own values filled in."""
    reading = VoiceReading.read(instrument, ChannelName.PULSE1)
    assert reading is not None

    performance = ChannelPerformance(voice_id=instrument.id)
    played: List[InstructionUnion] = []
    for _ in range(ticks):
        sounded = sound_tick(performance, reading)
        assert sounded is not None
        played.append(sounded)

    return played


class TestABendThroughTheSongWalk:
    def test_the_bend_an_envelope_writes_reaches_the_frame_a_tick_sounds(self) -> None:
        played = _played(_instrument(pitch=Envelope(items=(BEND, -BEND))), 2)

        assert [frame.detune for frame in played] == [BEND, -BEND]

    def test_both_dimensions_reach_the_frame_together(self) -> None:
        played = _played(
            _instrument(
                pitch=Envelope(items=(BEND,)),
                hi_pitch=Envelope(items=(COARSE_BEND,)),
            ),
            1,
        )

        assert played[0].detune == BEND
        assert played[0].coarse_detune == COARSE_BEND

    def test_a_voice_writing_no_bend_starts_unbent_after_one_that_bent(self) -> None:
        """A bend ends with the note that wrote it, so the next note sounds on its own divider."""
        bent = _instrument(
            pitch=Envelope(items=(BEND,)),
            hi_pitch=Envelope(items=(COARSE_BEND,)),
        )
        plain = _instrument()
        bent_reading = VoiceReading.read(bent, ChannelName.PULSE1)
        plain_reading = VoiceReading.read(plain, ChannelName.PULSE1)
        assert bent_reading is not None and plain_reading is not None

        performance = ChannelPerformance()
        apply_row(performance, Row(command=NoteOn(voice_id=bent.id)))
        sound_tick(performance, bent_reading)
        apply_row(performance, Row(command=NoteOn(voice_id=plain.id)))
        sounded = sound_tick(performance, plain_reading)

        assert isinstance(sounded, PulseInstruction)
        assert (sounded.detune, sounded.coarse_detune) == (0, 0)

    def test_a_bend_a_voice_writes_becomes_what_the_channel_holds(self) -> None:
        reading = VoiceReading.read(_instrument(pitch=Envelope(items=(BEND,))), ChannelName.PULSE1)
        assert reading is not None

        performance = ChannelPerformance(voice_id="written")
        sound_tick(performance, reading)

        assert performance.feature_values[FeatureKey.PITCH] == BEND


class TestABendUnderARowsModifiers:
    @pytest.mark.parametrize("transpose", (-SEMITONE, 0, SEMITONE), ids=("down", "none", "up"))
    def test_a_transpose_moves_the_note_and_leaves_the_bend_where_it_is(self, transpose: int) -> None:
        """A row states the note; how far off that note the frame sounds is the frame's own."""
        instruction = PulseInstruction(
            on=True,
            pitch=REFERENCE,
            volume=MAX_VOLUME,
            duty_cycle=0,
            detune=BEND,
            coarse_detune=COARSE_BEND,
        )

        sounded = apply_modifiers(instruction, transpose, MAX_VOLUME)

        assert sounded.pitch == REFERENCE + transpose
        assert sounded.detune == BEND
        assert sounded.coarse_detune == COARSE_BEND

    def test_a_row_volume_leaves_the_bend_where_it_is(self) -> None:
        instruction = PulseInstruction(
            on=True,
            pitch=REFERENCE,
            volume=MAX_VOLUME,
            duty_cycle=0,
            detune=BEND,
        )

        sounded = apply_modifiers(instruction, 0, MAX_VOLUME // 2)

        assert sounded.detune == BEND
