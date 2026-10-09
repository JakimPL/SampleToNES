from functools import partial
from typing import Dict, Final, Tuple

from automation.dearpygui.items.colors import read_theme, read_theme_colors
from automation.dearpygui.items.types import Item
from automation.screen import Screen
from automation.steps.instructions import load_library
from automation.worlds.home import one_worker_config
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_core.constants.enums import ChannelName, GeneratorName

GENERATOR_CHANNELS: Final[Dict[GeneratorName, ChannelName]] = {
    GeneratorName.PULSE: ChannelName.PULSE1,
    GeneratorName.TRIANGLE: ChannelName.TRIANGLE,
    GeneratorName.NOISE: ChannelName.NOISE,
}


def line_color(screen: Screen, line: str) -> Tuple[float, ...]:
    """The color the theme bound to ``line`` draws it in."""

    def read() -> Tuple[float, ...]:
        theme = read_theme(line)
        assert theme is not None, f"no theme is bound to '{line}'"
        return read_theme_colors(theme)[0]

    return screen.bridge.ask(read)


def channel_colors(screen: Screen, channel: ChannelName) -> Tuple[Tuple[float, ...], ...]:
    """The colors of the theme that every view naming ``channel`` paints from."""
    return screen.bridge.ask(lambda: read_theme_colors(CHANNEL_THEME_TAGS[channel]))


class TestTheGeneratorsOfALibrary:
    """A library lists a row per generator, each drawing its fragment's waveform and spectrum in its channel's
    color.

    The library loads and shows a row per generator. Each row is clicked in turn, and its waveform draws one
    line in a color of its channel's theme. The three generators end with three different colors.
    """

    def test_each_generator_draws_in_its_channels_color(self, screen: Screen) -> None:
        """Each generator's row draws a waveform and a spectrum in its own channel's color."""
        instructions = screen.instructions
        tree = instructions.library.tree
        waveform = instructions.waveform
        rows: Dict[GeneratorName, Item] = {}

        def a_row_per_generator(screen: Screen) -> None:
            load_library(screen, one_worker_config())

            for generator in GeneratorName:
                rows[generator] = screen.expect_item(
                    partial(tree.generator_row, generator), description=f"the {generator} row"
                )

        def each_draws_in_its_color(screen: Screen) -> None:
            colors: Dict[GeneratorName, Tuple[float, ...]] = {}
            for generator, row in rows.items():
                tree.click(row)

                lines = screen.expect(waveform.series, bool, description=f"the {generator} waveform")
                assert len(lines) == 1
                screen.expect(instructions.spectrum_bands, bool, description=f"the {generator} spectrum")
                colors[generator] = line_color(screen, lines[0])
                assert colors[generator] in channel_colors(screen, GENERATOR_CHANNELS[generator])

            assert len(set(colors.values())) == len(GeneratorName)

        screen.scenario(a_row_per_generator, each_draws_in_its_color).run()
