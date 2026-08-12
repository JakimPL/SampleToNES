import platform
from dataclasses import dataclass

import pytest

from sampletones_application.constants.keybindings import MACOS_SCHEME_NAME
from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

DISPLAY_SETTINGS_COMBINATION = "Ctrl+D"
DUPLICATE_FRAME_COMBINATION = "Ctrl+Ins"
CLONE_FRAME_COMBINATION = "Ctrl+Shift+Ins"


def _press(text: str) -> KeyEvent:
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


@pytest.fixture(name="macos", scope="session")
def macos_fixture() -> ShortcutScheme:
    """The scheme a Mac opens on, which a case reads on whichever platform the suite runs."""
    return ShortcutCatalog.load(KEYBINDINGS_DIRECTORY).get(MACOS_SCHEME_NAME)


@pytest.fixture(name="mac_keyboard")
def mac_keyboard_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reads combinations the way a Mac is labelled, so Super shows as Command."""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")


class TestDisplaySettingsKey:
    """Ctrl+D opens the display settings, which the order table gave to duplicate-frame before."""

    def test_the_display_settings_read_under_the_combination_they_answer(self, shipped: ShortcutScheme) -> None:
        assert shipped.shortcut(ShortcutId.DISPLAY_SETTINGS).display() == DISPLAY_SETTINGS_COMBINATION

    def test_the_order_table_leaves_the_display_settings_key_alone(self, shipped: ShortcutScheme) -> None:
        """The order table sees a press first, so it answering none is what lets the dialog open
        while the cursor sits in the table."""
        assert shipped.action(ShortcutCategory.ORDER, _press(DISPLAY_SETTINGS_COMBINATION)) is None


class TestDuplicateFrameKey:
    """Duplicate-frame reads as "insert a copy" beside the table's Insert and ``+``."""

    def test_duplicate_frame_reads_under_the_combination_it_answers(self, shipped: ShortcutScheme) -> None:
        assert shipped.shortcut(ShortcutId.ORDER_DUPLICATE_FRAME).display() == DUPLICATE_FRAME_COMBINATION

    def test_duplicate_frame_answers_its_press_in_the_order_table(self, shipped: ShortcutScheme) -> None:
        action = shipped.action(ShortcutCategory.ORDER, _press(DUPLICATE_FRAME_COMBINATION))

        assert action is ShortcutId.ORDER_DUPLICATE_FRAME

    def test_clone_frame_reads_under_the_combination_it_answers(self, shipped: ShortcutScheme) -> None:
        assert shipped.shortcut(ShortcutId.ORDER_CLONE_FRAME).display() == CLONE_FRAME_COMBINATION

    def test_clone_frame_answers_its_press_in_the_order_table(self, shipped: ShortcutScheme) -> None:
        """Shift is what separates the deep copy from the repeat, so the two keys stay adjacent."""
        action = shipped.action(ShortcutCategory.ORDER, _press(CLONE_FRAME_COMBINATION))

        assert action is ShortcutId.ORDER_CLONE_FRAME

    def test_adding_a_frame_keeps_the_unmodified_insert(self, shipped: ShortcutScheme) -> None:
        assert shipped.action(ShortcutCategory.ORDER, _press("Ins")) is ShortcutId.ORDER_ADD_FRAME


class TestSelectKeys(BaseTestSuite):
    """The A chord is selection and nothing else, each modifier narrowing the shape it names."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        category: ShortcutCategory
        shortcut_id: ShortcutId
        expected: str

    test_cases = (
        TestCase(
            label="the whole frame",
            category=ShortcutCategory.TRACKER,
            shortcut_id=ShortcutId.TRACKER_SELECT_ALL,
            expected="Ctrl+A",
        ),
        TestCase(
            label="a column",
            category=ShortcutCategory.TRACKER,
            shortcut_id=ShortcutId.TRACKER_SELECT_COLUMN,
            expected="Ctrl+Shift+A",
        ),
        TestCase(
            label="a subcolumn",
            category=ShortcutCategory.TRACKER,
            shortcut_id=ShortcutId.TRACKER_SELECT_SUBCOLUMN,
            expected="Ctrl+Alt+A",
        ),
        TestCase(
            label="the whole order",
            category=ShortcutCategory.ORDER,
            shortcut_id=ShortcutId.ORDER_SELECT_ALL,
            expected="Ctrl+A",
        ),
        TestCase(
            label="an order row",
            category=ShortcutCategory.ORDER,
            shortcut_id=ShortcutId.ORDER_SELECT_ROW,
            expected="Ctrl+Shift+A",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_shape_reads_under_the_combination_it_answers(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        assert shipped.shortcut(test_case.shortcut_id).display() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_shape_answers_its_press_in_the_grid_that_states_it(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        action = shipped.action(test_case.category, _press(test_case.expected))

        assert action is test_case.shortcut_id

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_mac_reaches_the_shape_through_its_own_modifier(
        self,
        test_case: TestCase,
        macos: ShortcutScheme,
    ) -> None:
        """A Mac spells the chord with Command, so the family reads the same on either keyboard."""
        combination = test_case.expected.replace("Ctrl", "Cmd")

        assert macos.action(test_case.category, _press(combination)) is test_case.shortcut_id


class TestDisplacedSettingsKeys(BaseTestSuite):
    """Where the two settings the A chord displaced now answer, each keeping its family's shape."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut_id: ShortcutId
        expected: str
        mac_expected: str

    test_cases = (
        TestCase(
            label="audio settings",
            shortcut_id=ShortcutId.AUDIO_SETTINGS,
            expected="Ctrl+U",
            mac_expected="Cmd+U",
        ),
        TestCase(
            label="advanced settings",
            shortcut_id=ShortcutId.TOGGLE_ADVANCED_SETTINGS,
            expected="Ctrl+Alt+T",
            mac_expected="Cmd+Alt+T",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_setting_reads_under_the_combination_it_answers(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        assert shipped.shortcut(test_case.shortcut_id).display() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_setting_answers_its_press_wherever_no_grid_claims_it(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        action = shipped.action(ShortcutCategory.APPLICATION, _press(test_case.expected))

        assert action is test_case.shortcut_id

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_setting_reads_under_the_combination_a_mac_gives_it(
        self,
        test_case: TestCase,
        macos: ShortcutScheme,
        mac_keyboard: None,
    ) -> None:
        assert macos.shortcut(test_case.shortcut_id).display() == test_case.mac_expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_grids_leave_the_settings_key_alone(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        """A grid is asked before the application is, so a dialog opens while the cursor stands in one."""
        press = _press(test_case.expected)

        assert shipped.action(ShortcutCategory.TRACKER, press) is None
        assert shipped.action(ShortcutCategory.ORDER, press) is None


class TestChannelKeys(BaseTestSuite):
    """The four channels sit on the four function keys, in the order the tracker shows them."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut_id: ShortcutId
        expected: str

    test_cases = (
        TestCase(label="pulse 1", shortcut_id=ShortcutId.TOGGLE_CHANNEL_PULSE_1, expected="F1"),
        TestCase(label="pulse 2", shortcut_id=ShortcutId.TOGGLE_CHANNEL_PULSE_2, expected="F2"),
        TestCase(label="triangle", shortcut_id=ShortcutId.TOGGLE_CHANNEL_TRIANGLE, expected="F3"),
        TestCase(label="noise", shortcut_id=ShortcutId.TOGGLE_CHANNEL_NOISE, expected="F4"),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_channel_reads_under_the_function_key_it_answers(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        assert shipped.shortcut(test_case.shortcut_id).display() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_channel_key_reaches_it_from_every_tab(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        """The action is the application's, so the key answers wherever no panel claims it."""
        action = shipped.action(ShortcutCategory.APPLICATION, _press(test_case.expected))

        assert action is test_case.shortcut_id

    def test_the_samples_panel_keeps_rename_on_its_function_key(self, shipped: ShortcutScheme) -> None:
        """A panel is asked before the application is, so F2 renames while the samples list has
        the keyboard and switches Pulse 2 everywhere else."""
        assert shipped.action(ShortcutCategory.SAMPLES, _press("F2")) is ShortcutId.SAMPLES_RENAME_SAMPLE


class TestTrackerAdjustKeys(BaseTestSuite):
    """The keys the tracker's shifts answer to: Ctrl carries pitch, Alt carries volume, and Shift
    makes the step the bigger one."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut_id: ShortcutId
        expected: str

    test_cases = (
        TestCase(label="transpose up", shortcut_id=ShortcutId.TRACKER_TRANSPOSE_UP, expected="Ctrl+Up"),
        TestCase(label="transpose down", shortcut_id=ShortcutId.TRACKER_TRANSPOSE_DOWN, expected="Ctrl+Down"),
        TestCase(
            label="an octave up",
            shortcut_id=ShortcutId.TRACKER_TRANSPOSE_OCTAVE_UP,
            expected="Ctrl+Shift+Up",
        ),
        TestCase(
            label="an octave down",
            shortcut_id=ShortcutId.TRACKER_TRANSPOSE_OCTAVE_DOWN,
            expected="Ctrl+Shift+Down",
        ),
        TestCase(label="volume up", shortcut_id=ShortcutId.TRACKER_VOLUME_UP, expected="Alt+Up"),
        TestCase(label="volume down", shortcut_id=ShortcutId.TRACKER_VOLUME_DOWN, expected="Alt+Down"),
        TestCase(
            label="a coarse volume up",
            shortcut_id=ShortcutId.TRACKER_VOLUME_UP_COARSE,
            expected="Alt+Shift+Up",
        ),
        TestCase(
            label="a coarse volume down",
            shortcut_id=ShortcutId.TRACKER_VOLUME_DOWN_COARSE,
            expected="Alt+Shift+Down",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_shift_reads_under_the_combination_it_answers(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        assert shipped.shortcut(test_case.shortcut_id).display() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_shift_answers_its_press_in_the_tracker(
        self,
        test_case: TestCase,
        shipped: ShortcutScheme,
    ) -> None:
        action = shipped.action(ShortcutCategory.TRACKER, _press(test_case.expected))

        assert action is test_case.shortcut_id


class TestMacosAdjustKeys(BaseTestSuite):
    """What a Mac reaches the tracker's shifts through.

    The alternatives a Mac keyboard needs already answer on Cmd and Alt with the arrows, so the
    shifts take Cmd+Alt there and read their axis from the direction: the arrows up and down carry
    pitch, those left and right carry volume, and Shift makes the step the bigger one.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut_id: ShortcutId
        expected: str

    test_cases = (
        TestCase(label="transpose up", shortcut_id=ShortcutId.TRACKER_TRANSPOSE_UP, expected="Cmd+Alt+Up"),
        TestCase(label="transpose down", shortcut_id=ShortcutId.TRACKER_TRANSPOSE_DOWN, expected="Cmd+Alt+Down"),
        TestCase(
            label="an octave up",
            shortcut_id=ShortcutId.TRACKER_TRANSPOSE_OCTAVE_UP,
            expected="Cmd+Alt+Shift+Up",
        ),
        TestCase(
            label="an octave down",
            shortcut_id=ShortcutId.TRACKER_TRANSPOSE_OCTAVE_DOWN,
            expected="Cmd+Alt+Shift+Down",
        ),
        TestCase(label="volume up", shortcut_id=ShortcutId.TRACKER_VOLUME_UP, expected="Cmd+Alt+Right"),
        TestCase(label="volume down", shortcut_id=ShortcutId.TRACKER_VOLUME_DOWN, expected="Cmd+Alt+Left"),
        TestCase(
            label="a coarse volume up",
            shortcut_id=ShortcutId.TRACKER_VOLUME_UP_COARSE,
            expected="Cmd+Alt+Shift+Right",
        ),
        TestCase(
            label="a coarse volume down",
            shortcut_id=ShortcutId.TRACKER_VOLUME_DOWN_COARSE,
            expected="Cmd+Alt+Shift+Left",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_shift_reads_under_the_combination_a_mac_gives_it(
        self,
        test_case: TestCase,
        macos: ShortcutScheme,
        mac_keyboard: None,
    ) -> None:
        assert macos.shortcut(test_case.shortcut_id).display() == test_case.expected


class TestMacosKeys(BaseTestSuite):
    """What a Mac reads its keys as, spelled the way that keyboard is labelled."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut_id: ShortcutId
        expected: str

    test_cases = (
        TestCase(label="save", shortcut_id=ShortcutId.SAVE_PROJECT, expected="Cmd+S"),
        TestCase(label="undo", shortcut_id=ShortcutId.UNDO, expected="Cmd+Z"),
        TestCase(label="redo", shortcut_id=ShortcutId.REDO, expected="Cmd+Shift+Z"),
        TestCase(label="exit", shortcut_id=ShortcutId.EXIT, expected="Cmd+Q"),
        TestCase(label="fullscreen", shortcut_id=ShortcutId.TOGGLE_FULLSCREEN, expected="Cmd+Ctrl+F"),
        TestCase(label="playback stays on the space bar", shortcut_id=ShortcutId.PLAY, expected="Space"),
        TestCase(
            label="a channel keeps its function key", shortcut_id=ShortcutId.TOGGLE_CHANNEL_PULSE_1, expected="F1"
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_an_action_reads_under_the_combination_a_mac_gives_it(
        self,
        test_case: TestCase,
        macos: ShortcutScheme,
        mac_keyboard: None,
    ) -> None:
        assert macos.shortcut(test_case.shortcut_id).display() == test_case.expected


class TestMacosAlternatives(BaseTestSuite):
    """The keys a Mac laptop keyboard omits, each reachable by a combination it carries."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        category: ShortcutCategory
        combination: str
        expected: ShortcutId

    test_cases = (
        TestCase(
            label="the first row",
            category=ShortcutCategory.TRACKER,
            combination="Cmd+Up",
            expected=ShortcutId.TRACKER_FIRST_ROW,
        ),
        TestCase(
            label="the last row",
            category=ShortcutCategory.TRACKER,
            combination="Cmd+Down",
            expected=ShortcutId.TRACKER_LAST_ROW,
        ),
        TestCase(
            label="a page up",
            category=ShortcutCategory.TRACKER,
            combination="Alt+Up",
            expected=ShortcutId.TRACKER_PAGE_UP,
        ),
        TestCase(
            label="a page down",
            category=ShortcutCategory.TRACKER,
            combination="Alt+Down",
            expected=ShortcutId.TRACKER_PAGE_DOWN,
        ),
        TestCase(
            label="clearing a row",
            category=ShortcutCategory.TRACKER,
            combination="Cmd+Backspace",
            expected=ShortcutId.TRACKER_CLEAR_ROW,
        ),
        TestCase(
            label="the first frame",
            category=ShortcutCategory.ORDER,
            combination="Cmd+Left",
            expected=ShortcutId.ORDER_FIRST_POSITION,
        ),
        TestCase(
            label="the last frame",
            category=ShortcutCategory.ORDER,
            combination="Cmd+Right",
            expected=ShortcutId.ORDER_LAST_POSITION,
        ),
        TestCase(
            label="adding a frame",
            category=ShortcutCategory.ORDER,
            combination="Cmd+Enter",
            expected=ShortcutId.ORDER_ADD_FRAME,
        ),
        TestCase(
            label="a sample to the top",
            category=ShortcutCategory.SAMPLES,
            combination="Cmd+Alt+Up",
            expected=ShortcutId.SAMPLES_MOVE_SAMPLE_TO_TOP,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_alternative_reaches_the_action_its_missing_key_reaches(
        self,
        test_case: TestCase,
        macos: ShortcutScheme,
    ) -> None:
        action = macos.action(test_case.category, _press(test_case.combination))

        assert action is test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_key_it_stands_in_for_still_answers(
        self,
        test_case: TestCase,
        macos: ShortcutScheme,
    ) -> None:
        """A Mac with a full keyboard finds the plain key where every other platform has it."""
        combinations = macos.shortcut(test_case.expected).combinations()

        assert all(
            macos.claimant(test_case.category, combination) is test_case.expected for combination in combinations
        )
