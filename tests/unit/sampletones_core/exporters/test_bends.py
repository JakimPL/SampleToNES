from typing import Final, List, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import PulseExporter, TriangleExporter
from sampletones_core.features import resting_held_features
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import PulseInstruction, TriangleInstruction

REFERENCE: Final[int] = 60
VOLUME: Final[int] = 12
BENDS: Final[Tuple[int, ...]] = (0, 3, -5, 12)
COARSE_BENDS: Final[Tuple[int, ...]] = (0, 1, -2, 0)


def _pulses() -> List[PulseInstruction]:
    return [
        PulseInstruction(
            on=True,
            pitch=REFERENCE,
            volume=VOLUME,
            duty_cycle=1,
            detune=detune,
            coarse_detune=coarse_detune,
        )
        for detune, coarse_detune in zip(BENDS, COARSE_BENDS)
    ]


class TestReadingBendsOutOfAStream:
    def test_both_dimensions_come_back_frame_by_frame(self) -> None:
        written = PulseExporter.read_envelopes(_pulses(), REFERENCE)

        assert written[FeatureKey.PITCH] == BENDS
        assert written[FeatureKey.HI_PITCH] == COARSE_BENDS

    def test_a_rest_carries_the_bend_the_last_sounding_frame_stated(self) -> None:
        instructions = [
            PulseInstruction(on=True, pitch=REFERENCE, volume=VOLUME, duty_cycle=0, detune=9),
            PulseInstruction.null_instruction(),
            PulseInstruction(on=True, pitch=REFERENCE, volume=VOLUME, duty_cycle=0, detune=-4),
        ]

        written = PulseExporter.read_envelopes(instructions, REFERENCE)

        assert written[FeatureKey.PITCH] == (9, 9, -4)

    def test_a_rest_before_the_first_sounding_frame_takes_its_bend(self) -> None:
        instructions = [
            PulseInstruction.null_instruction(),
            PulseInstruction(on=True, pitch=REFERENCE, volume=VOLUME, duty_cycle=0, detune=6),
        ]

        written = PulseExporter.read_envelopes(instructions, REFERENCE)

        assert written[FeatureKey.PITCH] == (6, 6)

    def test_a_channel_that_never_sounds_carries_no_bend(self) -> None:
        written = PulseExporter.read_envelopes([PulseInstruction.null_instruction()] * 3, REFERENCE)

        assert written[FeatureKey.PITCH] == (0, 0, 0)
        assert written[FeatureKey.HI_PITCH] == (0, 0, 0)


class TestRoundTrip:
    def test_a_bent_stream_survives_the_trip_through_its_envelopes(self) -> None:
        instructions = _pulses()

        features = PulseExporter.to_features(instructions, REFERENCE, ())

        assert list(PulseExporter.from_features(features))[: len(instructions)] == instructions

    def test_the_triangle_carries_its_bend_the_same_way(self) -> None:
        instructions = [TriangleInstruction(on=True, pitch=REFERENCE, detune=detune) for detune in BENDS]

        features = TriangleExporter.to_features(instructions, REFERENCE, ())

        assert list(TriangleExporter.from_features(features))[: len(instructions)] == instructions

    def test_a_dimension_left_to_the_channel_sounds_the_note_itself(self) -> None:
        features = PulseExporter.to_features(
            _pulses(),
            REFERENCE,
            (FeatureKey.PITCH, FeatureKey.HI_PITCH),
        )

        assert features.envelope(FeatureKey.PITCH).items == ()
        assert all(not instruction.bent for instruction in PulseExporter.from_features(features))


class TestChannelsThatOfferTheBend:
    @pytest.mark.parametrize(
        "channel_name",
        (ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE),
        ids=lambda channel_name: str(channel_name),
    )
    def test_a_tonal_channel_records_both_bend_dimensions(self, channel_name: ChannelName) -> None:
        held = resting_held_features(channel_name)

        assert FeatureKey.PITCH in held
        assert FeatureKey.HI_PITCH in held

    def test_the_noise_channel_records_neither(self) -> None:
        held = resting_held_features(ChannelName.NOISE)

        assert FeatureKey.PITCH not in held
        assert FeatureKey.HI_PITCH not in held


class TestBendEnvelopesOnAnInstrument:
    def test_a_bend_envelope_reaches_the_frames_an_instrument_plays(self) -> None:
        from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
        from sampletones_core.project.voices.instrument import Instrument

        instrument = Instrument(
            name="bent",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(VOLUME, VOLUME)),
                pitch=Envelope(items=(4, -4)),
            ),
            initial_pitch=REFERENCE,
        )

        frames = instrument.instructions(ChannelName.PULSE1)

        assert [frame.detune for frame in frames] == [4, -4]
