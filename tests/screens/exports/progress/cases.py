from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Tuple

from automation.boundaries.dialogs import DialogKind
from automation.dearpygui.keys import IMGUI_ESCAPE
from automation.screen import Screen
from automation.steps.sequencer import open_voice_menu
from automation.vocabulary.exports import EXPORT_INSTRUMENT
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_core.exports.stage import ExportStage
from sampletones_shared.paths.extensions import (
    EXT_FILE_BITPHASE,
    EXT_FILE_INSTRUMENT,
    EXT_FILE_JSON,
    EXT_FILE_MODULE,
    EXT_FILE_NSF,
)
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, PAD


def click_cancel(screen: Screen) -> None:
    """Clicks Cancel in the export window."""
    screen.exports.progress.cancel()


def press_escape(screen: Screen) -> None:
    """Presses Escape to cancel the export."""
    screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])


@dataclass(frozen=True)
class ExportDoor:
    """One door an export starts from: what it starts, what the window lists first, and how the user cancels it.

    Attributes:
        name: The folder the door writes into, named after the door.
        start: Starts the export into the folder it is given, answering the dialogs it opens.
        first_stage: The stage the run reports first, which the window lists.
        cancel: The user's gesture that cancels the run.
        project: Whether the export writes a project, whose outcome appears in the project notice.
    """

    name: str
    start: Callable[[Screen, Path], None]
    first_stage: ExportStage
    cancel: Callable[[Screen], None]
    project: bool


def from_the_file_menu(item: MenuElements, extension: str) -> Callable[[Screen, Path], None]:
    """Builds the start of a project export chosen from the File menu, saving as the arranged project."""

    def start(screen: Screen, into: Path) -> None:
        screen.answer_next_dialog(DialogKind.SAVE, into / f"{ARRANGED_PROJECT.stem}{extension}")
        screen.exports.export_project(item)

    return start


def from_the_reconstruction_menu(item: MenuElements, extension: str) -> Callable[[Screen, Path], None]:
    """Builds the start of an export chosen from the Reconstruction menu, saving as the playable reconstruction."""

    def start(screen: Screen, into: Path) -> None:
        screen.answer_next_dialog(DialogKind.SAVE, into / f"{PLAYABLE_RECONSTRUCTION.stem}{extension}")
        screen.exports.export_reconstruction(item)

    return start


def through_the_nsf_window(menu_start: Callable[[Screen], None], stem: str) -> Callable[[Screen, Path], None]:
    """Builds the start of an NSF export: opens the window with ``menu_start``, picks the file named ``stem``
    and presses Export.
    """

    def start(screen: Screen, into: Path) -> None:
        window = screen.exports.nsf
        menu_start(screen)
        screen.expect(window.is_shown, bool, description="the NSF window")
        screen.answer_next_dialog(DialogKind.SAVE, into / f"{stem}{EXT_FILE_NSF}")
        window.browse()
        screen.expect(
            lambda: screen.dialog_requests()[-1].answer == into / f"{stem}{EXT_FILE_NSF}",
            bool,
            description="the file chosen",
        )
        window.export()

    return start


def from_the_voice_menu(screen: Screen, into: Path) -> None:
    """Starts the export of one instrument from its right-click menu, saving as the instrument's name."""
    screen.answer_next_dialog(DialogKind.SAVE, into / f"{PAD}{EXT_FILE_INSTRUMENT}")
    open_voice_menu(screen, PAD)
    screen.context_menu.choose(screen.words(EXPORT_INSTRUMENT))


PROJECT_DOORS: Final[Tuple[ExportDoor, ...]] = (
    ExportDoor(
        name="module",
        start=from_the_file_menu(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER, EXT_FILE_MODULE),
        first_stage=ExportStage.WRITING,
        cancel=click_cancel,
        project=True,
    ),
    ExportDoor(
        name="bitphase",
        start=from_the_file_menu(MenuElements.ITEM_FILE_EXPORT_BITPHASE, EXT_FILE_BITPHASE),
        first_stage=ExportStage.WRITING,
        cancel=press_escape,
        project=True,
    ),
    ExportDoor(
        name="program",
        start=through_the_nsf_window(
            lambda screen: screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_NSF),
            ARRANGED_PROJECT.stem,
        ),
        first_stage=ExportStage.WALKING,
        cancel=click_cancel,
        project=True,
    ),
)

INSTRUMENT_DOORS: Final[Tuple[ExportDoor, ...]] = (
    ExportDoor(
        name="instruments",
        start=from_the_reconstruction_menu(
            MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_FAMITRACKER,
            EXT_FILE_INSTRUMENT,
        ),
        first_stage=ExportStage.WRITING,
        cancel=click_cancel,
        project=False,
    ),
    ExportDoor(
        name="presets",
        start=from_the_reconstruction_menu(
            MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_BITPHASE_PRESET,
            EXT_FILE_JSON,
        ),
        first_stage=ExportStage.WRITING,
        cancel=press_escape,
        project=False,
    ),
    ExportDoor(
        name="sample program",
        start=through_the_nsf_window(
            lambda screen: screen.exports.export_reconstruction(
                MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_NSF
            ),
            PLAYABLE_RECONSTRUCTION.stem,
        ),
        first_stage=ExportStage.WALKING,
        cancel=click_cancel,
        project=False,
    ),
    ExportDoor(
        name="instrument",
        start=from_the_voice_menu,
        first_stage=ExportStage.WRITING,
        cancel=click_cancel,
        project=False,
    ),
)
