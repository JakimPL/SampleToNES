from dataclasses import dataclass
from typing import List, Mapping

from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import Slot, channel_groups


@dataclass(frozen=True)
class ColumnGroup:
    """The channels one column of candidates answers, named by the channel standing for them.

    Attributes:
        generator: The generator of the lowest channel in the group, which stands for it.
        drive: The level every channel of the group reaches for.
    """

    generator: GeneratorUnion
    drive: float


def column_groups(
    remaining: Mapping[ChannelName, GeneratorUnion],
    drives: Mapping[ChannelName, float],
) -> List[ColumnGroup]:
    """One group per generator class and drive among ``remaining``, in channel order.

    The channels group as the joint assignment's layout groups them (``channel_groups``). Channels
    of one kind a stem drives alike share a candidate catalog and a scale, so one scored column
    answers all of them and the lowest of them stands for the group; successive picks over channels
    of one kind therefore reach the lowest free one. Channels of one kind at different drives are
    groups of their own, each scored at the level its stem gives it.

    Args:
        remaining: The channels still free that the stem may occupy, with their generators.
        drives: The level the stem gives each of its channels.

    Returns:
        The groups the stem offers, in the order their representative channels stand in.
    """
    slots = [
        Slot(channel_name=channel_name, kind=remaining[channel_name].class_name(), drive=drives[channel_name])
        for channel_name in ChannelName.items()
        if channel_name in remaining
    ]
    return [
        ColumnGroup(generator=remaining[slots[group.places[0]].channel_name], drive=group.drive)
        for group in channel_groups(slots)
    ]
