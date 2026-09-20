from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators import GeneratorUnion


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

    Channels of one kind a stem drives alike share a candidate catalog and a scale, so one
    scored column answers all of them and the lowest of them stands for the group; successive
    picks over channels of one kind therefore reach the lowest free one. Channels of one kind at
    different drives are groups of their own, each scored at the level its stem gives it.

    Args:
        remaining: The channels still free that the stem may occupy, with their generators.
        drives: The level the stem gives each of its channels.

    Returns:
        The groups the stem offers, in the order their representative channels stand in.
    """
    groups: Dict[Tuple[GeneratorClassName, float], ColumnGroup] = {}
    for channel_name in ChannelName.items():
        generator = remaining.get(channel_name)
        if generator is None:
            continue

        drive = drives[channel_name]
        groups.setdefault((generator.class_name(), drive), ColumnGroup(generator=generator, drive=drive))

    return list(groups.values())
