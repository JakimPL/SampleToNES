from typing import Dict, Final

import msgpack
import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.data import DataModel
from sampletones_core.instructions import PulseInstruction
from sampletones_shared.exceptions import DeserializationError
from sampletones_shared.types.data import SerializedData

PITCH: Final[int] = 60
VOLUME: Final[int] = 15


def _without(payload: bytes, *field_names: str) -> bytes:
    """The payload as a build that had never heard of ``field_names`` would have written it."""
    data: SerializedData = msgpack.unpackb(payload, raw=False)
    for field_name in field_names:
        data.pop(field_name, None)

    return bytes(msgpack.packb(data, use_bin_type=True))


class TestFieldsAPayloadLeavesOut:
    """A file written before a field existed still loads, taking that field's default.

    Serialization keys every field by name, so a payload from an older build simply says nothing
    about a field added since. What it means to say nothing is what the field defaults to, which
    is how a stored reconstruction or instruction library keeps loading as the model grows.
    """

    def test_a_field_the_payload_omits_takes_its_default(self) -> None:
        instruction = PulseInstruction(on=True, pitch=PITCH, volume=VOLUME, duty_cycle=1, detune=7)

        older = _without(instruction.serialize(), "detune", "coarse_detune")
        loaded = PulseInstruction.deserialize(older)

        assert loaded.detune == 0
        assert loaded.coarse_detune == 0
        assert loaded.timer_offset == 0

    def test_the_fields_a_payload_states_come_back_as_written(self) -> None:
        instruction = PulseInstruction(
            on=True,
            pitch=PITCH,
            volume=VOLUME,
            duty_cycle=1,
            detune=-3,
            coarse_detune=2,
        )

        assert PulseInstruction.deserialize(instruction.serialize()) == instruction

    def test_the_rest_of_the_payload_survives_the_omission(self) -> None:
        instruction = PulseInstruction(on=True, pitch=PITCH, volume=VOLUME, duty_cycle=1)

        loaded = PulseInstruction.deserialize(_without(instruction.serialize(), "detune"))

        assert loaded.pitch == PITCH
        assert loaded.volume == VOLUME
        assert loaded.duty_cycle == 1


class _Levels(DataModel):
    """A model carrying one value per channel, the shape a mapping field takes."""

    levels: Dict[ChannelName, float]


class TestAMappingField:
    """A mapping field is written key by key and read back keyed by the type it declares."""

    def test_a_mapping_survives_a_round_trip(self) -> None:
        model = _Levels(levels={ChannelName.PULSE1: 1.5, ChannelName.NOISE: 0.25})

        loaded = _Levels.deserialize(model.serialize())

        assert loaded.levels == {ChannelName.PULSE1: 1.5, ChannelName.NOISE: 0.25}
        assert all(isinstance(key, ChannelName) for key in loaded.levels)

    def test_a_mapping_is_written_under_plain_words(self) -> None:
        model = _Levels(levels={ChannelName.TRIANGLE: 2.0})

        written: SerializedData = msgpack.unpackb(model.serialize(), raw=False)

        assert written["levels"] == {"triangle": 2.0}

    def test_a_value_that_is_no_mapping_is_refused(self) -> None:
        with pytest.raises(DeserializationError, match="expects a mapping"):
            _Levels.deserialize(bytes(msgpack.packb({"levels": [1.0]}, use_bin_type=True)))
