from typing import Final

import msgpack

from sampletones_core.instructions import PulseInstruction
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
