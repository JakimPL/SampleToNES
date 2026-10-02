from pathlib import Path
from typing import Callable, Final, Optional, Tuple, TypeVar, Union

from sampletones_application.categories.key.text import TextKeyTuple
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.general import (
    TAG_GLOBAL_DIALOG_ERROR,
    TAG_GLOBAL_DIALOG_FILE_NOT_FOUND,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.tags.main import TAG_MAIN_EXPLORER_TREE
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from tests.suite.scenario import BaseTestScenario, ScenarioStep
from tests.suite.screens.boundaries.dialogs import DialogKind, DialogRequest, ScriptedFileDialogs
from tests.suite.screens.boundaries.errors import ErrorRecords
from tests.suite.screens.dearpygui.bridge import Bridge, ExpectationError
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import Item, WindowReading, read_viewport_title, read_windows
from tests.suite.screens.dearpygui.screenshot import capture
from tests.suite.screens.dearpygui.windows import WindowManager
from tests.suite.screens.keyboard import press_combination, primary_combination
from tests.suite.screens.render_thread import QueueRenderThread
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.display_settings import DisplaySettings
from tests.suite.screens.views.instructions import Instructions
from tests.suite.screens.views.main import Main
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.notices import Notice
from tests.suite.screens.views.project import Project
from tests.suite.screens.views.reconstructions import Reconstructions
from tests.suite.screens.views.sequencer import Sequencer
from tests.suite.screens.views.tabs import Tabs

ReadingT = TypeVar("ReadingT")

EXPECT_TIMEOUT_SECONDS: Final[float] = 10.0
STEP_SEPARATOR: Final[str] = " → "
SCREENSHOT_SUFFIX: Final[str] = ".png"


class Screen:
    """What a scenario holds: SampleToNES on its display, a user's hand on it, and the views it reads.

    A scenario speaks through views, one per tab, card and dialog. A view knows where its controls
    stand and reads what they show, so the scenario states gestures and expectations in a user's
    terms. A reading taken while the application still moves is waited for with ``expect``, which
    reads once a frame until the expectation holds.
    """

    def __init__(
        self,
        *,
        bridge: Bridge,
        render_thread: QueueRenderThread,
        hand: Hand,
        window_manager: WindowManager,
        language: LanguageManager,
        shortcuts: ShortcutManager,
        dialogs: ScriptedFileDialogs,
        errors: ErrorRecords,
        artifacts: Path,
    ) -> None:
        self.bridge = bridge
        self.hand = hand
        self._window_manager = window_manager
        self._render_thread = render_thread
        self._shortcuts = shortcuts
        self._dialogs = dialogs
        self._errors = errors
        self._artifacts = artifacts
        self._language = language
        self.tabs = Tabs(bridge, hand)
        self.menu = MenuBar(bridge, language)
        self.display_settings = DisplaySettings(bridge, hand, self.menu)
        self.project = Project(bridge, hand, self.menu)
        self.main = Main(bridge, hand, language)
        self.explorer = FileTree(bridge, hand, TAG_MAIN_EXPLORER_TREE)
        self.reconstructions = Reconstructions(bridge, hand, self.menu)
        self.sequencer = Sequencer(bridge, self.menu)
        self.instructions = Instructions(bridge, hand)
        self.error_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_ERROR)
        self.file_not_found_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_FILE_NOT_FOUND)

    def expect(
        self,
        reading: Callable[[], ReadingT],
        holds: Callable[[ReadingT], bool],
        *,
        description: str,
    ) -> ReadingT:
        """Takes ``reading`` once a frame until ``holds`` accepts it, and returns that reading."""
        return self.bridge.expect(
            reading,
            holds,
            description=description,
            timeout=EXPECT_TIMEOUT_SECONDS,
        )

    def words(self, key: Union[str, TextKeyTuple]) -> str:
        """What the language file says under ``key``, which is what the application shows the user."""
        return self._language[key]

    def expect_item(
        self,
        reading: Callable[[], Optional[Item]],
        *,
        description: str,
    ) -> Item:
        """Takes ``reading`` once a frame until it finds an item, and returns the item.

        Raises:
            ExpectationError: If no item is found within the expectation's time.
        """
        found = self.expect(reading, lambda value: value is not None, description=description)
        if found is None:
            raise ExpectationError(f"Expected {description}, and found nothing")

        return found

    def frames(self, count: int) -> None:
        """Lets ``count`` frames pass, for a scenario whose promise is itself a number of frames."""
        self.bridge.frames(count)

    def capture(self, name: str) -> Path:
        """Keeps a picture of the next frame beside the scenario's other files, as evidence of a look."""
        return capture(self.bridge, (self._artifacts / name).with_suffix(SCREENSHOT_SUFFIX))

    def title(self) -> str:
        """The title on the window's title bar, which names the documents open."""
        return self.bridge.ask(read_viewport_title)

    def is_running(self) -> bool:
        """Whether the application still draws its window."""
        return self._render_thread.is_running()

    def close_window(self) -> None:
        """Closes the application's window from its title bar, the way a window manager asks it to."""
        self._window_manager.request_close()

    def wait_for_exit(self) -> bool:
        """Waits for the application to stop, and says whether it did within the expectation's time."""
        return self._render_thread.wait_stopped(EXPECT_TIMEOUT_SECONDS)

    def dialog_requests(self) -> Tuple[DialogRequest, ...]:
        """Every file dialog the application opened so far, in order."""
        return self._dialogs.requests

    def shown_windows(self) -> Tuple[WindowReading, ...]:
        """Every window standing on the screen besides the application's main one."""
        return tuple(
            window
            for window in self.bridge.ask(read_windows)
            if window.shown and window.alias != TAG_GLOBAL_WINDOW_MAIN
        )

    def answer_next_dialog(
        self,
        kind: DialogKind,
        path: Optional[Path],
    ) -> None:
        """Answers the next file dialog of ``kind`` with ``path``, or dismisses it for ``None``."""
        self._dialogs.answer(kind, path)

    def claim_error(self, naming: str) -> None:
        """Waits for the error a scenario provoked on purpose, one whose message holds ``naming``.

        A claimed error is the application reporting a failure as it should, so the after-checks leave
        it out. An error nobody claims still fails the scenario.
        """
        self.expect(
            lambda: self._errors.claim(naming),
            bool,
            description=f"an error naming '{naming}'",
        )

    def press_shortcut(self, shortcut_id: ShortcutId) -> None:
        """Presses the keys the scheme in place gives ``shortcut_id`` on the real keyboard."""
        press_combination(self.hand, primary_combination(self._shortcuts.shortcut(shortcut_id)))

    def scenario(self, *steps: Callable[["Screen"], None]) -> BaseTestScenario["Screen"]:
        """The ordered steps of one scenario, each named after its function in a failure it raises."""
        return BaseTestScenario(
            label=STEP_SEPARATOR.join(step.__name__ for step in steps),
            build=lambda: self,
            steps=[ScenarioStep(label=step.__name__, action=_named(step)) for step in steps],
        )


def _named(step: Callable[[Screen], None]) -> Callable[[Screen], None]:
    def action(screen: Screen) -> None:
        try:
            step(screen)
        except BaseException as error:
            error.add_note(f"In the step '{step.__name__}'")
            raise

    return action
