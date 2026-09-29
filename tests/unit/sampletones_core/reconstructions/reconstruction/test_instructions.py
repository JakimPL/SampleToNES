from typing import Final, List, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.instructions import InstructionData, InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem

CHANNEL: Final[ChannelName] = ChannelName.PULSE1
REFERENCE: Final[int] = 52
HELD: Final[Tuple[FeatureKey, ...]] = (FeatureKey.ARPEGGIO,)


def _pulse() -> PulseInstruction:
    return PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)


def _rest() -> PulseInstruction:
    return PulseInstruction.null_instruction()


def _created(stream: List[InstructionUnion]) -> InstructionsItem:
    return InstructionsItem.create(
        channel_name=CHANNEL,
        instructions=stream,
        initial_pitch=REFERENCE,
        held_features=HELD,
    )


class TestAStreamRestingThroughEveryFrame:
    """A channel resting throughout stands by, so its stream states no frame."""

    def test_it_stores_no_frame(self) -> None:
        item = _created([_rest(), _rest()])

        assert item.instructions == []
        assert not item.sounds

    def test_it_keeps_the_reference_it_was_given(self) -> None:
        item = _created([_rest(), _rest()])

        assert item.initial_pitch == REFERENCE
        assert tuple(item.held_features) == HELD

    def test_a_stored_one_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            InstructionsItem(
                channel_name=CHANNEL,
                instructions=[InstructionData.create(_rest())],
                initial_pitch=REFERENCE,
                held_features=list(HELD),
            )


class TestAStreamSoundingSomewhere:
    def test_it_keeps_every_frame_it_describes(self) -> None:
        stream = [_rest(), _pulse(), _rest()]

        item = _created(stream)

        assert [data.instruction for data in item.instructions] == stream
        assert item.sounds
