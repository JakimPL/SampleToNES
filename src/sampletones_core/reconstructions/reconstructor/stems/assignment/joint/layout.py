import itertools
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Self, Sequence, Tuple, TypeVar

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry

Placed = TypeVar("Placed")
GroupKey = Tuple[GeneratorClassName, float]
Places = Tuple[int, ...]


@dataclass(frozen=True)
class Slot:
    """One channel a stem may sound in a frame, with the kind it plays and the level the stem drives it at.

    A drive ``d`` asks the channel to play its part of the stem's audio ``d`` times louder, so the
    channel reads each row at ``1 / d²`` of its library power (``driven_powers``).

    Attributes:
        channel_name: The channel.
        kind: The generator class the channel plays.
        drive: The level the stem gives the channel.
    """

    channel_name: ChannelName
    kind: GeneratorClassName
    drive: float

    @property
    def plays_levels(self) -> bool:
        """Whether the channel sounds a note at more than one level, as every kind but the triangle does."""
        return self.kind != GeneratorClassName.TRIANGLE_GENERATOR


@dataclass(frozen=True)
class ChannelGroup:
    """Channels of one kind that a stem drives alike, which sound every row alike and so stand in for each other.

    A channel reads a row at its own drive (``Slot``), so channels of one kind at one drive sound a
    row the same. Any of them may play the row, and rows spread over them sound the same in any
    order. They fill lowest first, so a row the group sounds alone plays on its lowest channel.

    Attributes:
        kind: The generator class the group's channels play.
        drive: The level the stem gives each of them.
        places: The group's channels by their places in the layout, ascending.
    """

    kind: GeneratorClassName
    drive: float
    places: Places

    @property
    def shared(self) -> bool:
        """Whether two or more channels share the group, so its rows stand in more than one order."""
        return len(self.places) > 1


def channel_groups(slots: Sequence[Slot]) -> Tuple[ChannelGroup, ...]:
    """``slots`` grouped by kind and drive, each slot's place being its position in ``slots``.

    This is the one rule of which channels stand in for each other, which the joint assignment's
    layout and the picks assignment's columns both read. Each group's places ascend, and the groups
    stand in the order of their lowest places.
    """
    places: Dict[GroupKey, List[int]] = {}
    for place, slot in enumerate(slots):
        places.setdefault((slot.kind, slot.drive), []).append(place)

    return tuple(
        ChannelGroup(kind=kind, drive=drive, places=tuple(members)) for (kind, drive), members in places.items()
    )


@dataclass(frozen=True)
class StemLayout:
    """The channels one stem sounds a frame with, and how many of them it may sound at once.

    A channel's place is its position in ``slots``, which every combination of the stem's rows
    follows. The stem's channels fall into groups, each of one kind at one drive (``groups``):

    - within a group, channels sound a row alike, so they are interchangeable and fill lowest first;
    - across groups, a row sounds at each group's own level, so every placement of rows over the
      groups sounds distinct and is searched.

    Attributes:
        stem_id: The stem.
        slots: The channels the stem may occupy among those the run plays, in channel order.
        cap: The most channels the stem sounds in one frame.
    """

    stem_id: int
    slots: Tuple[Slot, ...]
    cap: int

    @classmethod
    def of(cls, entry: StemEntry, channels: Dict[ChannelName, GeneratorUnion]) -> Self:
        """The layout of one stem entry over the channels the run plays."""
        settings = entry.settings
        slots = tuple(
            Slot(channel_name=name, kind=channels[name].class_name(), drive=settings.drives[name])
            for name in ChannelName.items()
            if name in settings.channel_set and name in channels
        )
        return cls(stem_id=entry.id, slots=slots, cap=settings.channel_cap)

    @property
    def kinds(self) -> FrozenSet[GeneratorClassName]:
        """The kinds of channel the stem may sound."""
        return frozenset(slot.kind for slot in self.slots)

    @property
    def groups(self) -> Tuple[ChannelGroup, ...]:
        """The stem's channels grouped by kind and drive (``channel_groups``), in the order of their lowest channels."""
        return channel_groups(self.slots)

    @property
    def shared_groups(self) -> Tuple[ChannelGroup, ...]:
        """The groups two or more channels share, in the order of their lowest channels."""
        return tuple(group for group in self.groups if group.shared)

    def groups_of(self, kind: GeneratorClassName) -> Tuple[ChannelGroup, ...]:
        """The groups of the stem's channels of ``kind``, in the order of their lowest channels."""
        return tuple(group for group in self.groups if group.kind == kind)

    def first_place(self, kind: GeneratorClassName) -> int:
        """The place a row of ``kind`` sounding alone fills first: the lowest channel of the kind's first group.

        The stem must hold a channel of ``kind``.
        """
        return self.groups_of(kind)[0].places[0]

    def orders(self, values: Sequence[Placed]) -> List[Tuple[Placed, ...]]:
        """``values``, one per channel in layout order, in every order within each group.

        Every such order sounds the same, so whatever reads a combination once per sound may read it
        in any of them. The values' own order comes first, and it stands alone where every group
        holds one channel. The first group's orders vary slowest.
        """
        shared = [group.places for group in self.shared_groups]
        every = itertools.product(*(itertools.permutations(places) for places in shared))
        return [self._reordered(values, shared, permutations) for permutations in every]

    def of_kind(self, kind: GeneratorClassName) -> Tuple[Slot, ...]:
        """The stem's channels of one kind, in channel order."""
        return tuple(slot for slot in self.slots if slot.kind == kind)

    def places_of(self, kind: GeneratorClassName) -> Tuple[int, ...]:
        """The places of the stem's channels of one kind, in channel order."""
        return tuple(place for place, slot in enumerate(self.slots) if slot.kind == kind)

    def relative_level(self, place: int, other: int) -> float:
        """The level on the channel at ``place`` sounding a row as a level of one sounds it at ``other``.

        Each channel reads a row at ``1 / d²`` of its power (``driven_powers``), so the two channels
        sound a row alike at levels in the ratio ``(d_place / d_other)²``. Within a group it is one.
        """
        return (self.slots[place].drive / self.slots[other].drive) ** 2

    def gain(self, place: int) -> float:
        """How many times its power on the channel at ``place`` a row sounds when every channel of that kind plays it.

        Each channel reads the row at its own drive, and the channels add in power. Against the
        channel at ``place`` they sound the sum of their levels relative to it (``relative_level``),
        ``Σ_c (d_place / d_c)²``.
        """
        return sum(self.relative_level(place, other) for other in self.places_of(self.slots[place].kind))

    @staticmethod
    def _reordered(
        values: Sequence[Placed], groups: Sequence[Places], permutations: Sequence[Places]
    ) -> Tuple[Placed, ...]:
        """``values`` with each group's places, in turn, taking the values at the group's permutation of them."""
        reordered = list(values)
        for places, permutation in zip(groups, permutations):
            for target, source in zip(places, permutation):
                reordered[target] = values[source]

        return tuple(reordered)


def separate_layouts(stems_config: StemsConfig, channels: Dict[ChannelName, GeneratorUnion]) -> Tuple[StemLayout, ...]:
    """Every stem's layout, each channel held by one stem alone.

    A joint search settles each stem's channels together, which leaves no channel for two stems to
    compete for.

    Raises:
        ValueError: If two stems may occupy the same channel.
    """
    layouts = tuple(StemLayout.of(entry, channels) for entry in stems_config.entries)
    _refuse_shared_channels(layouts)
    return layouts


def _refuse_shared_channels(layouts: Sequence[StemLayout]) -> None:
    """Checks that no channel belongs to two of ``layouts``.

    Raises:
        ValueError: If two stems may occupy the same channel.
    """
    held: Dict[ChannelName, int] = {}
    for layout in layouts:
        for slot in layout.slots:
            if slot.channel_name in held:
                raise ValueError(
                    f"The joint assignment needs each channel held by one stem; stems {held[slot.channel_name]} "
                    f"and {layout.stem_id} both allow {slot.channel_name}"
                )

            held[slot.channel_name] = layout.stem_id
