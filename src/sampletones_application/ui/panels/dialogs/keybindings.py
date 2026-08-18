from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.settings import KeybindingsElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.tags.compose import compose_tag
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
    TAG_SETTINGS_KEYBINDINGS_PANEL_ACTIONS,
    TAG_SETTINGS_KEYBINDINGS_TABLE_ACTIONS,
    TAG_SETTINGS_KEYBINDINGS_TEXT_MESSAGE,
    TAG_SETTINGS_KEYBINDINGS_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyCombination, KeyRouter
from sampletones_application.utils.gui.keyboard.capture import KeyCapture
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.shared.keybindings import (
    KeybindingGroup,
    KeybindingRow,
    KeybindingsViewModel,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import StringCallback, VoidCallback

CombinationCallback = Callable[[KeyCombination], None]


class GUIKeybindingsWindow(GUIDialogWindow):
    """Modal form over the keys each action answers to, one row per action grouped by its scope.

    A row is given keys either way round: clicking its shortcut cell listens for the press to
    assign, and the entry box below writes a combination out for the actions a press cannot reach.
    Both report through their own hook, so the owner decides what an assignment means and this
    window shows what it decided.

    The action set is fixed, so the rows are built once per appearance and every later view re-reads
    their labels; the filter reaches the same rows through their visibility, which keeps a keystroke
    off the widget tree.
    """

    def __init__(
        self,
        *,
        layout: SettingsLayout,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._language_manager = language_manager
        self._layout = layout
        self._capture: Optional[KeyCapture] = None
        self._view_model: Optional[KeybindingsViewModel] = None
        self._filter = ""

        self.on_scheme_selected: Optional[StringCallback] = None
        self.on_action_selected: Optional[StringCallback] = None
        self.on_combination_typed: Optional[StringCallback] = None
        self.on_combination_captured: Optional[CombinationCallback] = None
        self.on_clear: Optional[VoidCallback] = None
        self.on_reset: Optional[VoidCallback] = None
        self.on_commit: Optional[VoidCallback] = None
        self.on_cancel: Optional[VoidCallback] = None

        self._lbl_unbound = self._label(KeybindingsElements.UNBOUND)
        self._msg_capturing = self._message(KeybindingsElements.CAPTURING)

        super().__init__(
            tag=TAG_SETTINGS_KEYBINDINGS_WINDOW,
            width=layout.keybindings.window.width,
            height=layout.keybindings.window.height,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def open(self, view_model: KeybindingsViewModel) -> None:
        """Shows the window listing the actions of the draft being edited."""
        self._view_model = view_model
        self._filter = ""
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The rendered values are seeded by :meth:`open` before the tree rebuilds."""

    def update_view(self, view_model: KeybindingsViewModel) -> None:
        """Re-reads the rows of the open window from the draft as it now stands."""
        self._view_model = view_model
        self._render()

    def create_window(self) -> None:
        with self.dialog_window(
            label=self._title(KeybindingsElements.WINDOW_TITLE),
            on_close=self._request_cancel,
        ):
            self._create_scheme_field()
            self._create_filter_field()
            self._create_action_list()
            dpg.add_separator()
            self._create_shortcut_field()
            dpg.add_text(tag=TAG_SETTINGS_KEYBINDINGS_TEXT_MESSAGE, default_value="")
            dpg.add_separator()
            self._create_action_buttons()

        self._bind_dialog_theme(
            TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME,
            TAG_SETTINGS_KEYBINDINGS_INPUT_FILTER,
            TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT,
        )

        self._install_capture()
        self._render()
        self._install_navigation(
            [
                FocusStop.field(TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME),
                FocusStop.field(TAG_SETTINGS_KEYBINDINGS_INPUT_FILTER),
                FocusStop.field(TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT),
                FocusStop.button(TAG_SETTINGS_KEYBINDINGS_BUTTON_CLEAR, self._request_clear),
                FocusStop.button(TAG_SETTINGS_KEYBINDINGS_BUTTON_RESET, self._request_reset),
                FocusStop.button(TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL, self._request_cancel),
                FocusStop.button(TAG_SETTINGS_KEYBINDINGS_BUTTON_OK, self._request_commit),
            ],
            on_escape=self._request_cancel,
        )

    def _create_scheme_field(self) -> None:
        view_model = self._require_view_model()
        with labeled_field(
            self._label(KeybindingsElements.SCHEME),
            self._layout.label_width,
        ):
            dpg.add_combo(
                tag=TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME,
                items=list(view_model.schemes),
                default_value=view_model.scheme,
                width=self._layout.combo_width,
                callback=self._on_scheme_changed,
            )

    def _create_filter_field(self) -> None:
        with labeled_field(
            self._label(KeybindingsElements.FILTER),
            self._layout.label_width,
        ):
            dpg.add_input_text(
                tag=TAG_SETTINGS_KEYBINDINGS_INPUT_FILTER,
                default_value="",
                width=self._layout.combo_width,
                callback=self._on_filter_changed,
            )

    def _create_action_list(self) -> None:
        with (
            dpg.child_window(
                tag=TAG_SETTINGS_KEYBINDINGS_PANEL_ACTIONS,
                height=self._layout.keybindings.list_height,
                border=True,
            ),
            dpg.table(
                tag=TAG_SETTINGS_KEYBINDINGS_TABLE_ACTIONS,
                header_row=True,
                policy=dpg.mvTable_SizingFixedFit,
                resizable=False,
                scrollY=False,
            ),
        ):
            dpg.add_table_column(
                label=self._label(KeybindingsElements.ACTION),
                init_width_or_weight=self._layout.keybindings.action_width,
            )
            dpg.add_table_column(label=self._label(KeybindingsElements.SHORTCUT))
            for group in self._require_view_model().groups:
                self._create_group(group)

    def _create_group(self, group: KeybindingGroup) -> None:
        with dpg.table_row(tag=compose_tag(PRE_SETTINGS_KEYBINDINGS_GROUP, group.category)):
            header = dpg.add_text(group.label)
            FontRegistry.bind_to_item(header, Font.BOLD)

        for row in group.rows:
            self._create_row(row)

    def _create_row(self, row: KeybindingRow) -> None:
        row_tag = compose_tag(PRE_SETTINGS_KEYBINDINGS_ROW, row.action)
        with dpg.table_row(tag=row_tag):
            dpg.add_selectable(
                tag=compose_tag(row_tag, SUF_SETTINGS_KEYBINDINGS_ACTION),
                label=row.label,
                user_data=row.action,
                callback=self._on_action_clicked,
            )
            dpg.add_selectable(
                tag=compose_tag(row_tag, SUF_SETTINGS_KEYBINDINGS_SHORTCUT),
                label=row.combination,
                user_data=row.action,
                callback=self._on_shortcut_clicked,
            )

    def _create_shortcut_field(self) -> None:
        with labeled_field(
            self._label(KeybindingsElements.SHORTCUT),
            self._layout.label_width,
        ):
            dpg.add_input_text(
                tag=TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT,
                default_value="",
                width=self._layout.combo_width,
                on_enter=True,
                callback=self._on_shortcut_typed,
            )
            GUIButton(
                tag=TAG_SETTINGS_KEYBINDINGS_BUTTON_CLEAR,
                label=self._label(KeybindingsElements.CLEAR_BUTTON),
                callback=self._request_clear,
            )

    @table_wrapper(columns=3)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_KEYBINDINGS_BUTTON_RESET,
            label=self._label(KeybindingsElements.RESET_BUTTON),
            callback=self._request_reset,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL,
            label=self._language_manager["global.dialog.label.cancel"],
            callback=self._request_cancel,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_KEYBINDINGS_BUTTON_OK,
            label=self._language_manager["global.dialog.label.ok"],
            callback=self._request_commit,
            width=-1,
        )

    def _install_capture(self) -> None:
        """Readies the capture that reads a press, cancelled by whatever a dialog is cancelled by."""
        self._capture = KeyCapture(
            key_router=self._router,
            cancel=self._shortcuts.shortcut(ShortcutId.DIALOG_CANCEL).combinations(),
        )
        self._capture.on_captured = self._report_captured
        self._capture.on_cancelled = self._render

    def _teardown(self) -> None:
        """Stops the capture this appearance armed before the keyboard claim is released."""
        if self._capture is not None:
            self._capture.stop()
            self._capture = None

        super()._teardown()

    def _render(self) -> None:
        """Shows each action's keys, the standing selection, and what the filter leaves listed."""
        view_model = self._require_view_model()
        dpg_set_value(TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME, view_model.scheme)
        dpg_set_value(TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT, view_model.combination)
        dpg_set_value(TAG_SETTINGS_KEYBINDINGS_TEXT_MESSAGE, view_model.message)
        for group in view_model.groups:
            self._render_group(group, view_model.selected)

    def _render_group(self, group: KeybindingGroup, selected: Optional[str]) -> None:
        listed = False
        for row in group.rows:
            matches = row.matches(self._filter)
            listed = listed or matches
            self._render_row(row, selected=selected, listed=matches)

        dpg_configure_item(
            compose_tag(PRE_SETTINGS_KEYBINDINGS_GROUP, group.category),
            show=listed,
        )

    def _render_row(
        self,
        row: KeybindingRow,
        *,
        selected: Optional[str],
        listed: bool,
    ) -> None:
        row_tag = compose_tag(PRE_SETTINGS_KEYBINDINGS_ROW, row.action)
        is_selected = row.action == selected
        dpg_configure_item(row_tag, show=listed)
        dpg_configure_item(
            compose_tag(row_tag, SUF_SETTINGS_KEYBINDINGS_ACTION),
            label=row.label,
        )
        dpg_set_value(compose_tag(row_tag, SUF_SETTINGS_KEYBINDINGS_ACTION), is_selected)
        dpg_configure_item(
            compose_tag(row_tag, SUF_SETTINGS_KEYBINDINGS_SHORTCUT),
            label=self._shortcut_label(row, is_selected=is_selected),
        )
        dpg_set_value(compose_tag(row_tag, SUF_SETTINGS_KEYBINDINGS_SHORTCUT), is_selected)

    def _shortcut_label(self, row: KeybindingRow, *, is_selected: bool) -> str:
        """What a row's shortcut cell reads: the prompt while it listens, its keys otherwise."""
        if is_selected and self._capture is not None and self._capture.is_listening:
            return self._msg_capturing

        return row.combination if row.combination else self._lbl_unbound

    def _on_scheme_changed(self, _sender: Sender, app_data: str) -> None:
        self.call(self.on_scheme_selected, app_data)

    def _on_filter_changed(self, _sender: Sender, app_data: str) -> None:
        self._filter = app_data
        self._render()

    def _on_action_clicked(
        self,
        _sender: Sender,
        _app_data: bool,
        user_data: str,
    ) -> None:
        self._stop_capture()
        self.call(self.on_action_selected, user_data)

    def _on_shortcut_clicked(
        self,
        _sender: Sender,
        _app_data: bool,
        user_data: str,
    ) -> None:
        """Selects the row and listens for the press that gives it keys."""
        self._stop_capture()
        self.call(self.on_action_selected, user_data)
        self._require_capture().start()
        self._render()

    def _on_shortcut_typed(self, _sender: Sender, app_data: str) -> None:
        self.call(self.on_combination_typed, app_data)

    def _report_captured(self, combination: KeyCombination) -> None:
        self.call(self.on_combination_captured, combination)

    def _stop_capture(self) -> None:
        if self._capture is not None:
            self._capture.stop()

    def _request_clear(self) -> None:
        self._stop_capture()
        self.call(self.on_clear)

    def _request_reset(self) -> None:
        self._stop_capture()
        self.call(self.on_reset)

    def _request_commit(self) -> None:
        self._stop_capture()
        self.call(self.on_commit)

    def _request_cancel(self) -> None:
        self._stop_capture()
        self.call(self.on_cancel)

    def _label(self, element: KeybindingsElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.LABEL,
            element,
        ]

    def _title(self, element: KeybindingsElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.TITLE,
            element,
        ]

    def _message(self, element: KeybindingsElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.MESSAGE,
            element,
        ]

    def _require_capture(self) -> KeyCapture:
        """The capture the open window arms.

        Raises:
            SystemError: when a press is listened for before the window builds its tree.
        """
        if self._capture is None:
            raise SystemError("The keybindings window listens for a press only while it is open")

        return self._capture

    def _require_view_model(self) -> KeybindingsViewModel:
        """The actions on screen.

        Raises:
            SystemError: when the window is drawn before :meth:`open` seeds it.
        """
        if self._view_model is None:
            raise SystemError("The keybindings window is drawn from a view model it was opened with")

        return self._view_model
