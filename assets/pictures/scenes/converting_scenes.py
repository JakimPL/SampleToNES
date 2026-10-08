from functools import partial
from pathlib import Path
from typing import Final

import pytest

from assets.pictures.demo import (
    SPECIFICATION,
    hit_recording,
    piece_folder,
    recordings_folder,
    stem_recording,
)
from assets.pictures.paths import guide_picture
from assets.pictures.writer import Pictures
from automation.screen import Screen
from automation.steps.instructions import load_library
from automation.steps.main import (
    RUN_TIMEOUT_SECONDS,
    choose_from_the_row_menu,
    explorer_row,
    gather,
)
from automation.views.prompts import MissingPromptError
from automation.worlds.home import one_worker_config
from sampletones_application.constants.output import OutputKind
from sampletones_application.tags.general import TAG_GLOBAL_CONTEXT_WINDOW
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
    TAG_INSTRUCTIONS_LIBRARY_PANEL,
)
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_SOURCE_PANEL,
)
from sampletones_core.constants.enums import ChannelName, GeneratorName
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS

PAGE: Final[str] = "converting"
ISOLATE: Final[str] = "main.converter.label.context_isolate"
KICK: Final[str] = "Kick"
DOCUMENTS: Final[str] = USER_PATH_DOCUMENTS.parent.name
SNARE: Final[str] = "Snare"
LEAD: Final[str] = "Lead"


def open_folder(screen: Screen, path: Path) -> None:
    """Opens the explorer's row of the folder at ``path`` where it stands closed."""
    set_folder(screen, path, open=True)


def close_folder(screen: Screen, path: Path) -> None:
    """Closes the explorer's row of the folder at ``path`` where it stands open."""
    set_folder(screen, path, open=False)


def set_folder(screen: Screen, path: Path, *, open: bool) -> None:
    """Clicks the explorer's row of the folder at ``path`` where it stands other than ``open`` asks."""
    row = explorer_row(screen, path)
    if screen.explorer.is_open(row) != open:
        screen.explorer.open_by_click(row)
        screen.expect(
            partial(screen.explorer.is_open, row),
            open.__eq__,
            description=f"{path.name} {'open' if open else 'closed'}",
        )


def gather_the_stems(screen: Screen) -> None:
    """Gathers the piece's stems into one mix, on the levels the demo's conversion gives them.

    The stems are gathered in the order their levels pick, which puts them all on the first level,
    and each later level's stem is then put on a level of its own, last level first, so the levels
    stand in the demo's order. Each level of the demo holds one stem.
    """
    levels = SPECIFICATION.conversion.piece.levels
    open_folder(screen, recordings_folder())
    open_folder(screen, piece_folder())
    gather(screen, *(stem_recording(name) for level in levels for name in level))
    screen.main.choose_output(OutputKind.MIXED)
    screen.expect(
        screen.main.converter.list.has_levels,
        bool,
        description="the levels drawn",
    )
    for level in reversed(levels[1:]):
        for name in level:
            choose_from_the_row_menu(screen, stem_recording(name), screen.words(ISOLATE))

    screen.expect(
        screen.main.converter.list.level_count,
        len(levels).__eq__,
        description="a level per stem",
    )


class ConvertingScenes:
    """The Main tab at work: the Filesystem browser with a recording's menu, the Converter card holding a mix,
    the Source settings card, a finished conversion, and the Instructions tab with a tone drawn.

    The browser lists the folders beside the home as well, under the home's own rows, and their names
    belong to the machine, so the browser's picture keeps them out: the home's last recording stands at
    the bottom of the view, which leaves at most a few rows below it, all of them folders of the checkout
    whose short names end before the picture's left edge, and the scene is drawn alone, once every other
    scene's home, named after the run that made it, has gone. The piece's folder stands open so the
    home's rows reach above the menu, which the window's bottom pushes up.

    The finished conversion takes the hit on every channel, which keeps its result apart from the one
    the demo tree holds, so the run ends with the question about loading it and no question about
    replacing a file.
    """

    @pytest.mark.alone
    def picture_filesystem_menu(self, screen: Screen, pictures: Pictures) -> None:
        close_folder(screen, Path.cwd() / DOCUMENTS)
        open_folder(screen, recordings_folder())
        open_folder(screen, piece_folder())
        home = explorer_row(screen, Path.cwd())
        kick = explorer_row(screen, hit_recording(KICK))
        snare = explorer_row(screen, hit_recording(SNARE))
        screen.hand.scroll_into_view(home)
        screen.hand.scroll_to_bottom(snare)
        screen.explorer.right_click_beside(kick)
        screen.expect(
            screen.context_menu.is_shown,
            bool,
            description="the recording's menu",
        )
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "filesystem-menu"),
            home,
            snare,
            TAG_GLOBAL_CONTEXT_WINDOW,
        )

    def picture_converter_levels(self, screen: Screen, pictures: Pictures) -> None:
        gather_the_stems(screen)
        screen.hand.scroll_into_view(TAG_MAIN_CONVERTER_PANEL)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "converter-levels"), TAG_MAIN_CONVERTER_PANEL)

    def picture_source_settings(self, screen: Screen, pictures: Pictures) -> None:
        listing = screen.main.converter.list
        open_folder(screen, recordings_folder())
        open_folder(screen, piece_folder())
        lead = stem_recording(LEAD)
        gather(screen, lead)
        listing.pick(lead)
        screen.expect(partial(listing.is_picked, lead), bool, description=f"{LEAD} picked")
        screen.hand.scroll_into_view(TAG_MAIN_SOURCE_PANEL)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "source-settings"), TAG_MAIN_SOURCE_PANEL)

    def picture_converter_done(self, screen: Screen, pictures: Pictures) -> None:
        converter = screen.main.converter
        open_folder(screen, recordings_folder())
        kick = hit_recording(KICK)
        gather(screen, kick)
        converter.list.tick(kick, ChannelName.PULSE2)
        screen.expect(
            partial(converter.list.channel_ticked, kick, ChannelName.PULSE2),
            bool,
            description=f"{KICK} on every channel",
        )
        converter.press_action()
        screen.bridge.expect(
            converter.end_prompt.is_shown,
            bool,
            description="the run's end",
            timeout=RUN_TIMEOUT_SECONDS,
        )
        prompt = converter.end_prompt.window()
        if prompt is None:
            raise MissingPromptError("The run's end asks nothing")

        screen.hand.scroll_into_view(TAG_MAIN_CONVERTER_PANEL)
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "converter-done"),
            TAG_MAIN_CONVERTER_PANEL,
            prompt.alias,
        )
        converter.end_prompt.cancel()

    def picture_instructions(self, screen: Screen, pictures: Pictures) -> None:
        load_library(screen, one_worker_config())
        tree = screen.instructions.library.tree
        row = screen.expect_item(
            partial(tree.generator_row, GeneratorName.PULSE),
            description="the pulse row",
        )
        tree.click(row)
        screen.expect(
            screen.instructions.waveform.series,
            bool,
            description="the pulse drawn",
        )
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "instructions"),
            TAG_INSTRUCTIONS_LIBRARY_PANEL,
            TAG_INSTRUCTIONS_INSTRUCTION_PANEL_WAVEFORM,
            TAG_INSTRUCTIONS_INSTRUCTION_PANEL_SPECTRUM,
        )
