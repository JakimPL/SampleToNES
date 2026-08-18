from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    PRE_SETTINGS_KEYBINDINGS_GROUP,
    PRE_SETTINGS_KEYBINDINGS_ROW,
    SUF_SETTINGS_KEYBINDINGS_ACTION,
    SUF_SETTINGS_KEYBINDINGS_SHORTCUT,
    TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL,
    TAG_SETTINGS_KEYBINDINGS_BUTTON_CLEAR,
    TAG_SETTINGS_KEYBINDINGS_BUTTON_OK,
    TAG_SETTINGS_KEYBINDINGS_BUTTON_RESET,
    TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME,
    TAG_SETTINGS_KEYBINDINGS_INPUT_FILTER,
    TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT,
    TAG_SETTINGS_KEYBINDINGS_TEXT_MESSAGE,
)
from sampletones_application.ui.panels.dialogs.keybindings import GUIKeybindingsWindow
from sampletones_application.utils.gui.keyboard import KeyCombination, KeyEvent, KeyRouter
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, CTRL_ALT, NO_MODIFIERS
from sampletones_application.view_model.shared.keybindings import (
    KeybindingGroup,
    KeybindingRow,
    KeybindingsViewModel,
)
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
UNBOUND_LABEL: Final[str] = LANGUAGE_MANAGER["settings.keybindings.label.unbound"]
CAPTURING_MESSAGE: Final[str] = LANGUAGE_MANAGER["settings.keybindings.message.capturing"]

SAVE_PROJECT: Final[str] = "SaveProject"
ABOUT_DIALOG: Final[str] = "AboutDialog"
TRACKER_NEXT_ROW: Final[str] = "TrackerNextRow"

SCHEMES: Final[Tuple[str, ...]] = ("default", "studio")


def row_tag(action: str) -> str:
    return compose_tag(PRE_SETTINGS_KEYBINDINGS_ROW, action)


def action_tag(action: str) -> str:
    return compose_tag(row_tag(action), SUF_SETTINGS_KEYBINDINGS_ACTION)


def shortcut_tag(action: str) -> str:
    return compose_tag(row_tag(action), SUF_SETTINGS_KEYBINDINGS_SHORTCUT)


def group_tag(category: str) -> str:
    return compose_tag(PRE_SETTINGS_KEYBINDINGS_GROUP, category)


def view_model(
    *,
    selected: Optional[str] = None,
    combination: str = "",
    message: str = "",
) -> KeybindingsViewModel:
    return KeybindingsViewModel(
        groups=(
            KeybindingGroup(
                category="application",
                label="Application",
                rows=(
                    KeybindingRow(action=SAVE_PROJECT, label="Save project", combination="Ctrl+S"),
                    KeybindingRow(action=ABOUT_DIALOG, label="About", combination=""),
                ),
            ),
            KeybindingGroup(
                category="tracker",
                label="Tracker",
                rows=(KeybindingRow(action=TRACKER_NEXT_ROW, label="Next row", combination="Down"),),
            ),
        ),
        schemes=SCHEMES,
        scheme="default",
        selected=selected,
        combination=combination,
        message=message,
    )


class Harness:
    """The window built on a router of its own, with the gestures a user makes spelled as methods."""

    def __init__(self, layout_config: LayoutConfig) -> None:
        self.router = KeyRouter()
        self.window = GUIKeybindingsWindow(
            layout=layout_config.settings,
            language_manager=LANGUAGE_MANAGER,
            key_router=self.router,
            shortcut_source=shipped_source(),
        )
        self.selected: List[str] = []
        self.typed: List[str] = []
        self.captured: List[KeyCombination] = []
        self.schemes: List[str] = []
        self.gestures: List[str] = []
        self.window.on_action_selected = self.selected.append
        self.window.on_combination_typed = self.typed.append
        self.window.on_combination_captured = self.captured.append
        self.window.on_scheme_selected = self.schemes.append
        self.window.on_clear = lambda: self.gestures.append("clear")
        self.window.on_reset = lambda: self.gestures.append("reset")
        self.window.on_commit = lambda: self.gestures.append("commit")
        self.window.on_cancel = lambda: self.gestures.append("cancel")

    def render(self, model: Optional[KeybindingsViewModel] = None) -> None:
        """Builds the widget tree for the given view, the way ``open`` does without a live frame."""
        self.window.update_view(model if model is not None else view_model())
        self.window.create_window()

    def show(self, model: KeybindingsViewModel) -> None:
        self.window.update_view(model)

    def click_action(self, action: str) -> None:
        dpg.get_item_callback(action_tag(action))(action_tag(action), True, action)

    def click_shortcut(self, action: str) -> None:
        dpg.get_item_callback(shortcut_tag(action))(shortcut_tag(action), True, action)

    def type_filter(self, text: str) -> None:
        dpg.get_item_callback(TAG_SETTINGS_KEYBINDINGS_INPUT_FILTER)(
            TAG_SETTINGS_KEYBINDINGS_INPUT_FILTER,
            text,
        )

    def type_shortcut(self, text: str) -> None:
        dpg.get_item_callback(TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT)(
            TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT,
            text,
        )

    def press(self, key: int, modifiers: frozenset = NO_MODIFIERS) -> None:
        self.router.route(KeyEvent(key=key, modifiers=modifiers))

    @staticmethod
    def press_button(tag: str) -> None:
        dpg.get_item_callback(compose_tag(tag, SUF_BUTTON))()

    @staticmethod
    def label_of(tag: str) -> str:
        label: str = dpg.get_item_configuration(tag)["label"]
        return label

    @staticmethod
    def is_shown(tag: str) -> bool:
        shown: bool = dpg.get_item_configuration(tag)["show"]
        return shown


@pytest.fixture(name="harness")
def harness_fixture(dpg_context: None, layout_config: LayoutConfig) -> Harness:
    return Harness(layout_config)


class TestActionList:
    def test_every_action_reaches_a_row(self, harness: Harness) -> None:
        harness.render()

        assert dpg.does_item_exist(row_tag(SAVE_PROJECT))
        assert dpg.does_item_exist(row_tag(ABOUT_DIALOG))
        assert dpg.does_item_exist(row_tag(TRACKER_NEXT_ROW))

    def test_every_scope_reaches_a_header(self, harness: Harness) -> None:
        harness.render()

        assert dpg.does_item_exist(group_tag("application"))
        assert dpg.does_item_exist(group_tag("tracker"))

    def test_a_row_reads_the_keys_its_action_answers(self, harness: Harness) -> None:
        harness.render()

        assert harness.label_of(shortcut_tag(SAVE_PROJECT)) == "Ctrl+S"

    def test_an_action_carrying_no_keys_reads_as_unassigned(self, harness: Harness) -> None:
        harness.render()

        assert harness.label_of(shortcut_tag(ABOUT_DIALOG)) == UNBOUND_LABEL

    def test_every_shipped_scheme_reaches_the_combo(self, harness: Harness) -> None:
        harness.render()

        assert dpg.get_item_configuration(TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME)["items"] == list(SCHEMES)

    def test_a_later_view_re_reads_the_rows_already_built(self, harness: Harness) -> None:
        harness.render()
        harness.show(
            KeybindingsViewModel(
                groups=(
                    KeybindingGroup(
                        category="application",
                        label="Application",
                        rows=(
                            KeybindingRow(action=SAVE_PROJECT, label="Save project", combination="Ctrl+Alt+B"),
                            KeybindingRow(action=ABOUT_DIALOG, label="About", combination=""),
                        ),
                    ),
                    KeybindingGroup(
                        category="tracker",
                        label="Tracker",
                        rows=(KeybindingRow(action=TRACKER_NEXT_ROW, label="Next row", combination="Down"),),
                    ),
                ),
                schemes=SCHEMES,
                scheme="default",
                selected=None,
                combination="",
                message="",
            )
        )

        assert harness.label_of(shortcut_tag(SAVE_PROJECT)) == "Ctrl+Alt+B"

    def test_the_message_line_shows_what_the_owner_reported(self, harness: Harness) -> None:
        harness.render(view_model(message="Ctrl+Nonsense names no key on the keyboard."))

        assert dpg.get_value(TAG_SETTINGS_KEYBINDINGS_TEXT_MESSAGE).startswith("Ctrl+Nonsense")

    def test_every_action_is_offered(self, harness: Harness) -> None:
        harness.render()

        assert dpg.does_item_exist(TAG_SETTINGS_KEYBINDINGS_BUTTON_CLEAR)
        assert dpg.does_item_exist(TAG_SETTINGS_KEYBINDINGS_BUTTON_RESET)
        assert dpg.does_item_exist(TAG_SETTINGS_KEYBINDINGS_BUTTON_OK)
        assert dpg.does_item_exist(TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL)


class TestFilter:
    def test_an_empty_filter_leaves_every_row_listed(self, harness: Harness) -> None:
        harness.render()

        assert harness.is_shown(row_tag(SAVE_PROJECT))
        assert harness.is_shown(row_tag(TRACKER_NEXT_ROW))

    def test_a_filter_leaves_only_the_rows_it_matches(self, harness: Harness) -> None:
        harness.render()
        harness.type_filter("row")

        assert harness.is_shown(row_tag(TRACKER_NEXT_ROW))
        assert not harness.is_shown(row_tag(SAVE_PROJECT))

    def test_a_filter_reads_the_keys_as_well_as_the_name(self, harness: Harness) -> None:
        harness.render()
        harness.type_filter("ctrl+s")

        assert harness.is_shown(row_tag(SAVE_PROJECT))
        assert not harness.is_shown(row_tag(TRACKER_NEXT_ROW))

    def test_a_scope_the_filter_empties_takes_its_header_with_it(self, harness: Harness) -> None:
        harness.render()
        harness.type_filter("row")

        assert harness.is_shown(group_tag("tracker"))
        assert not harness.is_shown(group_tag("application"))

    def test_clearing_the_filter_lists_every_row_again(self, harness: Harness) -> None:
        harness.render()
        harness.type_filter("row")
        harness.type_filter("")

        assert harness.is_shown(row_tag(SAVE_PROJECT))
        assert harness.is_shown(group_tag("application"))


class TestSelection:
    def test_clicking_an_action_reports_it(self, harness: Harness) -> None:
        harness.render()
        harness.click_action(SAVE_PROJECT)

        assert harness.selected == [SAVE_PROJECT]

    def test_clicking_a_shortcut_reports_the_action_too(self, harness: Harness) -> None:
        harness.render()
        harness.click_shortcut(SAVE_PROJECT)

        assert harness.selected == [SAVE_PROJECT]

    def test_the_selected_row_reads_as_selected(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT))

        assert dpg.get_value(action_tag(SAVE_PROJECT)) is True
        assert dpg.get_value(shortcut_tag(SAVE_PROJECT)) is True
        assert dpg.get_value(action_tag(ABOUT_DIALOG)) is False

    def test_the_entry_box_shows_the_selected_action_keys(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT, combination="Ctrl+S"))

        assert dpg.get_value(TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT) == "Ctrl+S"


class TestCapture:
    def test_clicking_a_shortcut_listens_for_a_press(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT))
        harness.click_shortcut(SAVE_PROJECT)
        harness.press(dpg.mvKey_G, CTRL_ALT)

        assert harness.captured == [KeyCombination(dpg.mvKey_G, CTRL_ALT)]

    def test_a_listening_cell_asks_for_the_press(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT))
        harness.click_shortcut(SAVE_PROJECT)

        assert harness.label_of(shortcut_tag(SAVE_PROJECT)) == CAPTURING_MESSAGE

    def test_a_cancelled_capture_leaves_the_cell_reading_its_keys(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT))
        harness.click_shortcut(SAVE_PROJECT)
        harness.press(dpg.mvKey_Escape)

        assert harness.captured == []
        assert harness.label_of(shortcut_tag(SAVE_PROJECT)) == "Ctrl+S"

    def test_clicking_an_action_listens_for_nothing(self, harness: Harness) -> None:
        """The name cell selects the row, which leaves the keyboard where it was."""
        harness.render(view_model(selected=SAVE_PROJECT))
        harness.click_action(SAVE_PROJECT)
        harness.press(dpg.mvKey_G, CTRL_ALT)

        assert harness.captured == []

    def test_selecting_another_row_stops_listening(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT))
        harness.click_shortcut(SAVE_PROJECT)
        harness.click_action(ABOUT_DIALOG)
        harness.press(dpg.mvKey_G, CTRL_ALT)

        assert harness.captured == []


class TestReportedGestures:
    def test_a_written_combination_is_reported_on_entry(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT))
        harness.type_shortcut("Ctrl+Alt+B")

        assert harness.typed == ["Ctrl+Alt+B"]

    def test_picking_a_scheme_reports_it(self, harness: Harness) -> None:
        harness.render()
        dpg.get_item_callback(TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME)(
            TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME,
            "studio",
        )

        assert harness.schemes == ["studio"]

    @pytest.mark.parametrize(
        "tag, gesture",
        [
            (TAG_SETTINGS_KEYBINDINGS_BUTTON_CLEAR, "clear"),
            (TAG_SETTINGS_KEYBINDINGS_BUTTON_RESET, "reset"),
            (TAG_SETTINGS_KEYBINDINGS_BUTTON_OK, "commit"),
            (TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL, "cancel"),
        ],
        ids=["clear", "reset", "commit", "cancel"],
    )
    def test_every_button_reports_what_it_stands_for(
        self,
        harness: Harness,
        tag: str,
        gesture: str,
    ) -> None:
        harness.render()
        harness.press_button(tag)

        assert harness.gestures == [gesture]

    def test_a_button_pressed_mid_capture_stops_listening(self, harness: Harness) -> None:
        harness.render(view_model(selected=SAVE_PROJECT))
        harness.click_shortcut(SAVE_PROJECT)
        harness.press_button(TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL)
        harness.press(dpg.mvKey_G, CTRL)

        assert harness.captured == []
