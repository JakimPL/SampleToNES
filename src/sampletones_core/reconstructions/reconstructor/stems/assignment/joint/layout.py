import itertools
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Self, Sequence, Tuple, TypeVar

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry

Placed = TypeVar("Placed")


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
class StemLayout:
    """The channels one stem sounds a frame with, and how many of them it may sound at once.

    A channel's place is its position in ``slots``, which every combination of the stem's rows
    follows.

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
    def interchangeable_pulses(self) -> Tuple[int, ...]:
        """The places of the stem's pulses where it holds two or more and drives them alike, empty otherwise.

        Pulses driven alike sound a note the same on either channel, so a combination sounds the same
        with their rows in any order.
        """
        pulses = self.places_of(GeneratorClassName.PULSE_GENERATOR)
        if len(pulses) < 2 or len({self.slots[place].drive for place in pulses}) != 1:
            return ()

        return pulses

    def pulse_orders(self, values: Sequence[Placed]) -> List[Tuple[Placed, ...]]:
        """``values``, one per channel in layout order, in every order of the stem's interchangeable pulses.

        Every order sounds the same, so whatever reads a combination once per sound may read it in
        any of them. The values' own order comes first, and it stands alone where no pulses are
        interchangeable.
        """
        pulses = self.interchangeable_pulses
        orders: List[Tuple[Placed, ...]] = []
        for order in itertools.permutations(pulses):
            reordered = list(values)
            for target, source in zip(pulses, order):
                reordered[target] = values[source]

            orders.append(tuple(reordered))

        return orders

    def of_kind(self, kind: GeneratorClassName) -> Tuple[Slot, ...]:
        """The stem's channels of one kind, in channel order."""
        return tuple(slot for slot in self.slots if slot.kind == kind)

    def places_of(self, kind: GeneratorClassName) -> Tuple[int, ...]:
        """The places of the stem's channels of one kind, in channel order."""
        return tuple(place for place, slot in enumerate(self.slots) if slot.kind == kind)

    def gain(self, place: int) -> float:
        """How many times its power on the channel at ``place`` a row sounds when every channel of that kind plays it.

        Each channel reads the row at its own drive ``d``, at ``1 / d²`` of its library power
        (``driven_powers``), and the channels add in power. Against the channel at ``place``, played
        at ``d_place``, they sound ``Σ_c (d_place / d_c)²``.
        """
        drive = self.slots[place].drive
        return sum((drive / slot.drive) ** 2 for slot in self.of_kind(self.slots[place].kind))


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
