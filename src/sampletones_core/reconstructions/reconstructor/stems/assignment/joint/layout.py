from dataclasses import dataclass
from typing import Dict, FrozenSet, Self, Tuple

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry


@dataclass(frozen=True)
class Slot:
    """One channel a stem may sound in a frame, with the kind it plays and the level the stem drives it at.

    Attributes:
        channel_name: The channel.
        kind: The generator class the channel plays.
        drive: The level the stem gives the channel, which every candidate's power divides by squared.
    """

    channel_name: ChannelName
    kind: GeneratorClassName
    drive: float


@dataclass(frozen=True)
class StemLayout:
    """The channels one stem sounds a frame with, and how many of them it may sound at once.

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

    def of_kind(self, kind: GeneratorClassName) -> Tuple[Slot, ...]:
        """The stem's channels of one kind, in channel order."""
        return tuple(slot for slot in self.slots if slot.kind == kind)

    @property
    def interchangeable_pulses(self) -> Tuple[int, ...]:
        """The places of the stem's pulses where it holds two or more and drives them alike, empty otherwise.

        Pulses driven alike sound a note the same on either channel, so a combination sounds the same
        with their rows in any order.
        """
        pulses = tuple(
            index for index, slot in enumerate(self.slots) if slot.kind == GeneratorClassName.PULSE_GENERATOR
        )
        if len(pulses) < 2 or len({self.slots[index].drive for index in pulses}) != 1:
            return ()

        return pulses


def separate_layouts(stems_config: StemsConfig, channels: Dict[ChannelName, GeneratorUnion]) -> Tuple[StemLayout, ...]:
    """Every stem's layout, each channel held by one stem alone.

    A joint search settles each stem's channels together, which leaves no channel for two stems to
    compete for.

    Raises:
        ValueError: If two stems may occupy the same channel.
    """
    layouts = tuple(StemLayout.of(entry, channels) for entry in stems_config.entries)
    held: Dict[ChannelName, int] = {}
    for layout in layouts:
        for slot in layout.slots:
            if slot.channel_name in held:
                raise ValueError(
                    f"The joint assignment needs each channel held by one stem; stems {held[slot.channel_name]} "
                    f"and {layout.stem_id} both allow {slot.channel_name}"
                )
            held[slot.channel_name] = layout.stem_id

    return layouts
