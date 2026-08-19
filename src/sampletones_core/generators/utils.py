from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.instructions import (
    INSTRUCTION_CLASS_MAP,
    InstructionUnion,
)

from .maps import (
    CHANNEL_CLASSES,
    GENERATOR_CLASS_MAP,
    INSTRUCTION_TO_GENERATOR_MAP,
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


def get_remaining_generator_classes(
    remaining_channels: Dict[ChannelName, GeneratorUnion],
) -> Dict[GeneratorClassName, GeneratorUnion]:
    """
    Maps each remaining generator class to its representative channel generator.

    Channels of one kind share a candidate catalogue, so one channel stands for the
    kind while its candidates are scored. The lowest remaining channel of a kind is
    its representative, which resolves successive picks over same-kind channels to
    the lowest free channel deterministically.
    """
    return {
        remaining_channels[name].class_name(): remaining_channels[name]
        for name in reversed(ChannelName.items())
        if name in remaining_channels
    }


def get_generator_by_instruction(
    instruction: InstructionUnion,
    remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
) -> GeneratorUnion:
    instruction_class_name = instruction.class_name()
    instruction_class = INSTRUCTION_CLASS_MAP[instruction_class_name]
    generator_class = INSTRUCTION_TO_GENERATOR_MAP[instruction_class]
    return remaining_generator_classes[generator_class.class_name()]
