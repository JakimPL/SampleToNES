from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName

from .maps import (
    CHANNEL_CLASSES,
    GENERATOR_CLASS_MAP,
)
from .types import GeneratorUnion


def get_generators_by_channels(
    config: Config,
    channel_names: List[ChannelName],
) -> Dict[ChannelName, GeneratorUnion]:
    names = channel_names.copy()
    if ChannelName.PULSE2 in names and not ChannelName.PULSE1 in names:
        names.remove(ChannelName.PULSE2)
        names.insert(0, ChannelName.PULSE1)

    return {name: CHANNEL_CLASSES[name](config, name) for name in names}


def get_generators_map(
    config: Config,
) -> Dict[GeneratorClassName, GeneratorUnion]:
    return {name: generator_class(config, name) for name, generator_class in GENERATOR_CLASS_MAP.items()}
