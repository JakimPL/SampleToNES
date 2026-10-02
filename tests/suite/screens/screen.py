from pathlib import Path
from typing import Callable, Final, Optional, TypeVar

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from tests.suite.scenario import BaseTestScenario, ScenarioStep
from tests.suite.screens.boundaries.dialogs import DialogKind, ScriptedFileDialogs
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.screenshot import capture
from tests.suite.screens.dearpygui.windows import WindowManager
from tests.suite.screens.keyboard import press_combination, primary_combination
from tests.suite.screens.render_thread import QueueRenderThread
from tests.suite.screens.views.display_settings import DisplaySettings
from tests.suite.screens.views.menus import MenuBar
from tests.suite.screens.views.project import Project
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
        artifacts: Path,
    ) -> None:
        self.bridge = bridge
        self.hand = hand
        self._window_manager = window_manager
        self._render_thread = render_thread
        self._shortcuts = shortcuts
        self._dialogs = dialogs
        self._artifacts = artifacts
        self.tabs = Tabs(bridge, hand)
        self.menu = MenuBar(bridge, language)
        self.display_settings = DisplaySettings(bridge, hand, self.menu)
        self.project = Project(bridge, hand, self.menu)

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

    def frames(self, count: int) -> None:
        """Lets ``count`` frames pass, for a scenario whose promise is itself a number of frames."""
        self.bridge.frames(count)

    def capture(self, name: str) -> Path:
        """Keeps a picture of the next frame beside the scenario's other files, as evidence of a look."""
        return capture(self.bridge, (self._artifacts / name).with_suffix(SCREENSHOT_SUFFIX))

    def is_running(self) -> bool:
        """Whether the application still draws its window."""
        return self._render_thread.is_running()

    def close_window(self) -> None:
        """Closes the application's window from its title bar, the way a window manager asks it to."""
        self._window_manager.request_close()

    def wait_for_exit(self) -> bool:
        """Waits for the application to stop, and says whether it did within the expectation's time."""
        return self._render_thread.wait_stopped(EXPECT_TIMEOUT_SECONDS)

    def answer_next_dialog(
        self,
        kind: DialogKind,
        path: Optional[Path],
    ) -> None:
        """Answers the next file dialog of ``kind`` with ``path``, or dismisses it for ``None``."""
        self._dialogs.answer(kind, path)

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
