from typing import Final

import pytest

from sampletones_application.layout.general.colors.channel import ChannelColors
from sampletones_application.ui.panels.instruction.colors import fragment_color
from sampletones_application.utils.palette.colors.written import LiteralColor, WrittenColor
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_map
from sampletones_core.instructions import InstructionUnion
from sampletones_core.instructions.implementation.noise import NoiseInstruction
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.instructions.implementation.triangle import TriangleInstruction
from sampletones_core.library import InstructionLibraryFragment
from sampletones_core.library.creator.creation import generate_instruction

CHANNEL_COLORS: Final[ChannelColors] = ChannelColors(
    pulse1=LiteralColor((240, 146, 86, 255)),
    pulse2=LiteralColor((242, 209, 95, 255)),
    triangle=LiteralColor((140, 193, 237, 255)),
    noise=LiteralColor((187, 184, 194, 255)),
)


def _fragment(
    generator_class: GeneratorClassName,
    instruction: InstructionUnion,
) -> InstructionLibraryFragment[InstructionUnion]:
    """One fragment as the library makes it, which is what the Instructions tab draws."""
    config = Config()
    window = Window.from_config(config)
    _, fragment = generate_instruction(
        get_generators_map(config),
        generator_class,
        instruction,
        get_feature_extractor(config, window),
    )
    return fragment


class TestTheColorAFragmentIsDrawnIn:
    @pytest.mark.parametrize(
        ("generator_class", "instruction", "expected"),
        [
            (
                GeneratorClassName.PULSE_GENERATOR,
                PulseInstruction.default_instruction(),
                CHANNEL_COLORS.pulse1,
            ),
            (
                GeneratorClassName.TRIANGLE_GENERATOR,
                TriangleInstruction.default_instruction(),
                CHANNEL_COLORS.triangle,
            ),
            (
                GeneratorClassName.NOISE_GENERATOR,
                NoiseInstruction.default_instruction(),
                CHANNEL_COLORS.noise,
            ),
        ],
        ids=["pulse", "triangle", "noise"],
    )
    def test_a_fragment_takes_the_color_of_the_channel_its_generator_is_heard_on(
        self,
        generator_class: GeneratorClassName,
        instruction: InstructionUnion,
        expected: WrittenColor,
    ) -> None:
        assert fragment_color(CHANNEL_COLORS, _fragment(generator_class, instruction)) == expected

    def test_the_three_generators_are_drawn_in_three_different_colors(self) -> None:
        colors = {
            fragment_color(CHANNEL_COLORS, _fragment(generator_class, instruction))
            for generator_class, instruction in (
                (GeneratorClassName.PULSE_GENERATOR, PulseInstruction.default_instruction()),
                (GeneratorClassName.TRIANGLE_GENERATOR, TriangleInstruction.default_instruction()),
                (GeneratorClassName.NOISE_GENERATOR, NoiseInstruction.default_instruction()),
            )
        }
        assert len(colors) == 3
