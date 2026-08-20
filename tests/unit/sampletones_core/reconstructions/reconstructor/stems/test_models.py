from typing import Final, FrozenSet

from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.stem import Stem
from sampletones_core.reconstructions.reconstructor.stems.models.hierarchy import StemHierarchy

PULSE_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset((ChannelName.PULSE1, ChannelName.PULSE2))


class TestStem:
    def test_is_frozen_and_hashable(self) -> None:
        stem = Stem(id=0, channels=PULSE_CHANNELS)
        assert stem == Stem(id=0, channels=PULSE_CHANNELS)
        assert hash(stem) == hash(Stem(id=0, channels=PULSE_CHANNELS))

    def test_fields(self) -> None:
        stem = Stem(id=0, channels=PULSE_CHANNELS)
        assert stem.id == 0
        assert stem.channels == PULSE_CHANNELS


class TestStemHierarchy:
    def test_fields(self) -> None:
        hierarchy = StemHierarchy(
            levels=((0,), (1, 2)),
            mode=HierarchyMode.ROUND_ROBIN,
        )
        assert hierarchy.levels == ((0,), (1, 2))
        assert hierarchy.mode == HierarchyMode.ROUND_ROBIN


class TestHierarchyMode:
    def test_values(self) -> None:
        assert tuple(HierarchyMode) == (HierarchyMode.ROUND_ROBIN, HierarchyMode.STRICT)
