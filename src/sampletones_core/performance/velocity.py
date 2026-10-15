import math
from typing import Dict, Optional

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.performance.modifiers import level_scales
from sampletones_shared.constants.music import MAX_VELOCITY, MIN_VELOCITY


def velocity_level(channel_name: ChannelName, velocity: int) -> Optional[int]:
    """The level a key struck at ``velocity`` plays at on a channel, or ``None`` where a level only gates it.

    The velocities share the levels evenly, the softest strike at the quietest level and the hardest at the
    loudest. The triangle answers ``None``, since its level decides only whether it sounds, so a soft
    strike there sounds as a hard one does.

    Args:
        channel_name: The channel the key sounds on.
        velocity: How hard the key was struck.

    Returns:
        Optional[int]: The level the note plays at, or ``None`` on a channel whose level only gates it.

    Raises:
        ValueError: If ``velocity`` lies outside the range a struck key reports.
    """
    if not MIN_VELOCITY <= velocity <= MAX_VELOCITY:
        raise ValueError(f"A struck key reports a velocity from {MIN_VELOCITY} to {MAX_VELOCITY}, not {velocity}")

    if not level_scales(channel_name):
        return None

    return math.ceil(velocity * MAX_VOLUME / MAX_VELOCITY)


def velocity_levels(velocity: int) -> Dict[ChannelName, int]:
    """The level a key struck at ``velocity`` plays at on each channel whose level a strike sets.

    The triangle's level only gates it, so the triangle is left out and keeps the level it has.

    Raises:
        ValueError: If ``velocity`` lies outside the range a struck key reports.
    """
    levels: Dict[ChannelName, int] = {}
    for channel_name in ChannelName.items():
        level = velocity_level(channel_name, velocity)
        if level is not None:
            levels[channel_name] = level

    return levels
