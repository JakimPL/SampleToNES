import operator
from pathlib import Path
from typing import List, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT
from tests.screens.exports.instruments.import_files.constants import FOLDER, IMPORT_INSTRUMENT, KEPT
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import open_voice_menu
from tests.suite.screens.views.history import HistoryLine, HistorySegment
from tests.suite.screens.vocabulary.exports import EXPORT_INSTRUMENT
from tests.suite.screens.worlds.songs import PAD


def kept_folder() -> Path:
    """Returns the folder of the home that keeps the exported instrument files, created when missing."""
    path = Path.cwd() / FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


def choose_import(screen: Screen) -> None:
    """Chooses Import instrument... on the menu the empty foot of the voice list opens."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.sequencer.voices.right_click_below_the_rows()
    screen.expect(screen.context_menu.is_shown, bool, description="the list's menu")
    screen.context_menu.choose(screen.words(IMPORT_INSTRUMENT))


def export_kept(screen: Screen) -> Path:
    """Exports the hand-written voice from its menu to the kept folder under the name :data:`KEPT`."""
    path = kept_folder() / f"{KEPT}{EXT_FILE_INSTRUMENT}"
    notice = screen.exports.file_notice
    screen.answer_next_dialog(DialogKind.SAVE, path)
    open_voice_menu(screen, PAD)
    screen.context_menu.choose(screen.words(EXPORT_INSTRUMENT))
    screen.expect(notice.is_shown, bool, description="the notice of the export")
    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice gone")
    return path


def segments(lines: Tuple[HistoryLine, ...]) -> List[Tuple[HistorySegment, ...]]:
    """Returns the segments of each history line, one tuple per line."""
    return [tuple(line.segments) for line in lines]
