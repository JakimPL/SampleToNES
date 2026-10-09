from typing import Any

from sampletones_application.layout.general.colors.channel import ChannelColors
from sampletones_application.utils.palette.colors.written import WrittenColor
from sampletones_core.features import generator_channel
from sampletones_core.generators import CLASS_NAME_TO_GENERATOR_MAP
from sampletones_core.library import InstructionLibraryFragment


def fragment_color(
    channel_colors: ChannelColors,
    fragment: InstructionLibraryFragment[Any],
) -> WrittenColor:
    """The color one library fragment is drawn in, which is its generator's own.

    A fragment names the generator that made it, and a generator is heard on a channel the
    application already paints by, so the waveform and the spectrum of a pulse fragment read as
    the pulse wherever they are shown.

    Args:
        channel_colors: The palette every view naming a channel paints from.
        fragment: The fragment being drawn.

    Returns:
        WrittenColor: The color its generator is known by.
    """
    generator_name = CLASS_NAME_TO_GENERATOR_MAP[fragment.generator_class]
    return channel_colors.for_channel(generator_channel(generator_name))
