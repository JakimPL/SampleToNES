from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Final, Iterator, Optional, Tuple, TypeVar, Union

import numpy as np

from sampletones_application.categories.context import channel_label, generator_label
from sampletones_application.categories.key.text import TextKeyTuple
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    TAG_GLOBAL_DIALOG_ERROR,
    TAG_GLOBAL_DIALOG_FILE_NOT_FOUND,
    TAG_GLOBAL_DIALOG_NO_AUDIO_OUTPUT,
    TAG_GLOBAL_STATUS_BAR,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.tags.main import TAG_MAIN_EXPLORER_TREE
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_core.constants.enums import ChannelName, GeneratorName
from tests.suite.scenario import BaseTestScenario, ScenarioStep
from tests.suite.screens.boundaries.audio import OutputRecord
from tests.suite.screens.boundaries.dialogs import DialogKind, DialogRequest, ScriptedFileDialogs
from tests.suite.screens.boundaries.errors import ErrorRecords
from tests.suite.screens.boundaries.highlights import HighlightPlace, TableHighlights
from tests.suite.screens.boundaries.reveals import FileManagerStandIn
from tests.suite.screens.dearpygui.bridge import Bridge, ExpectationError
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.colors import read_theme
from tests.suite.screens.dearpygui.items.reading import read_item_count
from tests.suite.screens.dearpygui.items.regions import WindowReading, read_windows
from tests.suite.screens.dearpygui.items.texts import read_label, read_visible_text
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.items.viewport import read_pointer, read_viewport_title
from tests.suite.screens.dearpygui.recording import FrameRecording
from tests.suite.screens.dearpygui.screenshot import capture, drawn_frame
from tests.suite.screens.dearpygui.windows import WindowManager
from tests.suite.screens.keyboard import press_combination, primary_combination
from tests.suite.screens.render_thread import QueueRenderThread
from tests.suite.screens.views.audio_settings import AudioSettings
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.context_menu import ContextMenu
from tests.suite.screens.views.display_settings import DisplaySettings
from tests.suite.screens.views.exports import Exports
from tests.suite.screens.views.instructions import Instructions
from tests.suite.screens.views.keyboard_settings import KeyboardSettings
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
STATUS_BAR: Final[str] = compose_tag(TAG_GLOBAL_STATUS_BAR, SUF_BUTTON)
PIXEL_CHANNELS: Final[int] = 4


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
        file_manager: FileManagerStandIn,
        highlights: TableHighlights,
        output: OutputRecord,
        artifacts: Path,
    ) -> None:
        self.bridge = bridge
        self.hand = hand
        self._window_manager = window_manager
        self._render_thread = render_thread
        self._shortcuts = shortcuts
        self._dialogs = dialogs
        self._errors = errors
        self._file_manager = file_manager
        self._highlights = highlights
        self._output = output
        self._artifacts = artifacts
        self._language = language
        self.tabs = Tabs(bridge, hand)
        self.menu = MenuBar(bridge, hand, language)
        self.display_settings = DisplaySettings(bridge, hand, self.menu)
        self.keyboard_settings = KeyboardSettings(bridge, hand, self.menu)
        self.audio_settings = AudioSettings(bridge, hand)
        self.project = Project(bridge, hand, self.menu)
        self.main = Main(bridge, hand, language)
        self.context_menu = ContextMenu(bridge, hand)
        self.explorer = FileTree(bridge, hand, TAG_MAIN_EXPLORER_TREE)
        self.reconstructions = Reconstructions(bridge, hand, self.menu)
        self.sequencer = Sequencer(bridge, hand, self.menu)
        self.instructions = Instructions(bridge, hand)
        self.exports = Exports(bridge, hand, self.menu)
        self.error_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_ERROR)
        self.file_not_found_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_FILE_NOT_FOUND)
        self.no_output_notice = Notice(bridge, hand, TAG_GLOBAL_DIALOG_NO_AUDIO_OUTPUT)

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

    def shortcut_words(self, shortcut_id: ShortcutId) -> str:
        """How a menu prints the keys of ``shortcut_id`` under the scheme in place."""
        return self._shortcuts.shortcut(shortcut_id).display()

    def frame_pixels(self) -> np.ndarray:
        """The next frame drawn, as rows of pixels of red, green, blue and alpha fractions."""
        frame = drawn_frame(self.bridge)
        return np.frombuffer(frame.pixels, dtype=np.float32).reshape(frame.height, frame.width, PIXEL_CHANNELS)

    def channel_words(self, channel: ChannelName) -> str:
        """The name every display gives ``channel``."""
        return channel_label(self._language, channel)

    def generator_words(self, generator: GeneratorName) -> str:
        """The words the application names ``generator`` by wherever it offers one."""
        return generator_label(self._language, generator)

    def status(self) -> str:
        """What the status bar along the bottom of the window says."""
        return self.bridge.ask(lambda: read_label(STATUS_BAR))

    def shows_text(self, words: str) -> bool:
        """Whether text reading ``words`` was drawn in the last frame, such as a tooltip standing open."""
        return self.bridge.ask(lambda: read_visible_text(words))

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

    def pointer(self) -> Point:
        """Where the pointer stands in the viewport, as the application last saw it."""
        return self.bridge.ask(read_pointer)

    def theme_of(self, item: Item) -> Optional[str]:
        """The tag of the theme bound to ``item``, which is how a control wears a state such as hover."""
        return self.bridge.ask(lambda: read_theme(item))

    def item_count(self) -> int:
        """How many items the interface holds, which a gesture repeated without end leaves where it stood."""
        return self.bridge.ask(read_item_count)

    @contextmanager
    def record(self, reading: Callable[[], ReadingT]) -> Iterator[FrameRecording[ReadingT]]:
        """Takes ``reading`` on the render thread after every frame drawn while the block runs.

        ``reading`` runs between frames on the render thread, so it reads DearPyGui directly.
        """
        recording = FrameRecording(self._render_thread, reading)
        recording.start()
        try:
            yield recording
        finally:
            recording.stop()

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

    def sound_heard(self) -> int:
        """How many samples carrying sound the application has played so far, which grows while anything sounds.

        The count is taken at the output device, so a sound shorter than the frames between two readings counts
        all the same.
        """
        return self._output.sounding_samples()

    def dialog_requests(self) -> Tuple[DialogRequest, ...]:
        """Every file dialog the application opened so far, in order."""
        return self._dialogs.requests

    def revealed(self) -> Tuple[Path, ...]:
        """Every path the application asked the desktop's file manager to show, in order."""
        return self._file_manager.shown()

    def table_highlights(self) -> Dict[HighlightPlace, Tuple[float, ...]]:
        """Every highlight standing on a table, with the color the application laid it in."""
        return self._highlights.standing()

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

    def answer_next_save_as(
        self,
        path: Path,
        type_name: str,
    ) -> None:
        """Answers the next save dialog with ``path``, the offered file type named ``type_name`` picked in
        it.
        """
        self._dialogs.answer_save_as(path, type_name)

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

    def forgive_known_error(self, naming: str) -> None:
        """Claims every error holding ``naming``, which a defect the bugs ledger records provokes by chance.

        A scenario about something else stays quiet about a defect its gestures may meet, while the
        scenario reproducing the defect holds it to account.
        """
        while self._errors.claim(naming):
            continue

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
