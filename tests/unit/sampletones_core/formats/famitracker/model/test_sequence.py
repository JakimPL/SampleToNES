import pytest

from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
    SequenceKind,
)


class TestSequenceItemLimit:
    def test_a_sequence_at_the_limit_is_accepted(self) -> None:
        sequence = InstrumentSequence(kind=SequenceKind.VOLUME, items=tuple(range(MAX_SEQUENCE_ITEMS)))
        assert len(sequence.items) == MAX_SEQUENCE_ITEMS

    def test_a_sequence_beyond_the_limit_raises(self) -> None:
        with pytest.raises(ValueError, match=str(MAX_SEQUENCE_ITEMS)):
            InstrumentSequence(kind=SequenceKind.VOLUME, items=tuple(range(MAX_SEQUENCE_ITEMS + 1)))
