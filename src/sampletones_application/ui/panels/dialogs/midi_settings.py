from typing import Callable, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.tags.settings import (
    TAG_SETTINGS_MIDI_BUTTON_CANCEL,
    TAG_SETTINGS_MIDI_BUTTON_OK,
    TAG_SETTINGS_MIDI_BUTTON_REFRESH,
    TAG_SETTINGS_MIDI_CHECKBOX_VELOCITY,
    TAG_SETTINGS_MIDI_COMBO_PORT,
    TAG_SETTINGS_MIDI_TEXT_LAST_KEY,
    TAG_SETTINGS_MIDI_TEXT_MESSAGE,
    TAG_SETTINGS_MIDI_TEXT_UNAVAILABLE,
    TAG_SETTINGS_MIDI_TEXT_VELOCITY,
    TAG_SETTINGS_MIDI_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.seeded import GUISeededDialogWindow
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.shared.midi_settings import MidiSettingsViewModel
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

PortCallback = Callable[[Optional[str]], None]
VelocityCallback = Callable[[bool], None]


class GUIMidiSettingsWindow(GUISeededDialogWindow[MidiSettingsViewModel]):
    """The MIDI settings dialog: the input read, a refresh of the inputs, how velocity is read, and the key
    played last.

    Picking an input reports it through ``on_port_changed`` at once, so the reader tries the keyboard on the
    fields naming the key played last and its velocity before keeping it. ``on_commit`` keeps what the dialog
    shows, with the velocity setting it reports, and ``on_cancel`` puts back what the dialog opened with. On a
    computer offering no MIDI library the dialog says so in one line.
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
        self._no_input = language_manager["settings.midi.label.no_input"]

        self.on_port_changed: Optional[PortCallback] = None
        self.on_refresh: Optional[VoidCallback] = None
        self.on_commit: Optional[VelocityCallback] = None
        self.on_cancel: Optional[VoidCallback] = None

        super().__init__(
            subject="MIDI settings",
            tag=TAG_SETTINGS_MIDI_WINDOW,
            geometry=layout.midi.window,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    @property
    def is_open(self) -> bool:
        """Whether the dialog stands on the screen."""
        return bool(dpg.does_item_exist(self.tag) and dpg.is_item_shown(self.tag))

    def show_key(self, name: str, velocity: int) -> None:
        """Names the key played last and its velocity, while the dialog stands."""
        dpg_set_value(TAG_SETTINGS_MIDI_TEXT_LAST_KEY, name)
        dpg_set_value(TAG_SETTINGS_MIDI_TEXT_VELOCITY, str(velocity))

    def create_window(self) -> None:
        with self.dialog_window(
            label=self._language_manager["settings.midi.title.window_title"],
            on_close=self._request_cancel,
        ):
            if self.view_model.available:
                self._create_input_selection()
                self._create_velocity_choice()
                dpg.add_separator()
                dpg.add_text(tag=TAG_SETTINGS_MIDI_TEXT_MESSAGE)
                self._create_reading(
                    self._language_manager["settings.midi.label.last_key"],
                    TAG_SETTINGS_MIDI_TEXT_LAST_KEY,
                )
                self._create_reading(
                    self._language_manager["settings.midi.label.velocity"],
                    TAG_SETTINGS_MIDI_TEXT_VELOCITY,
                )
            else:
                dpg.add_text(
                    self._language_manager["settings.midi.message.unavailable"],
                    tag=TAG_SETTINGS_MIDI_TEXT_UNAVAILABLE,
                )

            dpg.add_separator()
            if self.view_model.available:
                self._create_buttons_with_refresh()
            else:
                self._create_action_buttons()

        if self.view_model.available:
            self._bind_dialog_theme(TAG_SETTINGS_MIDI_COMBO_PORT)

        self._render()
        self._install_navigation(self._focus_stops(), on_escape=self._request_cancel)

    def _focus_stops(self) -> List[FocusStop]:
        stops: List[FocusStop] = []
        if self.view_model.available:
            stops.extend(
                (
                    FocusStop.field(TAG_SETTINGS_MIDI_COMBO_PORT),
                    FocusStop.button(TAG_SETTINGS_MIDI_BUTTON_REFRESH, self._request_refresh),
                    FocusStop.field(TAG_SETTINGS_MIDI_CHECKBOX_VELOCITY),
                )
            )

        stops.extend(
            (
                FocusStop.button(TAG_SETTINGS_MIDI_BUTTON_CANCEL, self._request_cancel),
                FocusStop.button(TAG_SETTINGS_MIDI_BUTTON_OK, self._request_commit),
            )
        )
        return stops

    def _create_input_selection(self) -> None:
        with labeled_field(self._language_manager["settings.midi.label.input"], self._layout.label_width):
            dpg.add_combo(
                tag=TAG_SETTINGS_MIDI_COMBO_PORT,
                items=[],
                width=self._layout.combo_width,
                callback=self._on_port_changed,
            )

    def _create_velocity_choice(self) -> None:
        dpg.add_checkbox(
            tag=TAG_SETTINGS_MIDI_CHECKBOX_VELOCITY,
            label=self._language_manager["settings.midi.label.velocity_sets_volume"],
        )

    def _create_reading(self, label: str, tag: str) -> None:
        """Lays out one reading of the key played last, with its value in the mono font."""
        with labeled_field(label, self._layout.label_width):
            dpg.add_text(tag=tag)
            FontRegistry.bind_to_item(tag, Font.MONO)

    @table_wrapper(columns=3)
    def _create_buttons_with_refresh(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_MIDI_BUTTON_REFRESH,
            label=self._language_manager["settings.midi.label.refresh_button"],
            callback=self._request_refresh,
            width=-1,
        )
        self._add_cancel_and_ok()

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        self._add_cancel_and_ok()

    def _add_cancel_and_ok(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_MIDI_BUTTON_CANCEL,
            label=self._language_manager["global.dialog.label.cancel"],
            callback=self._request_cancel,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_MIDI_BUTTON_OK,
            label=self._language_manager["global.dialog.label.ok"],
            callback=self._request_commit,
            width=-1,
        )

    def _render(self) -> None:
        """Shows the inputs, the one read, the velocity setting, and why an input failed to open, if one did.

        The readings of the key played last start empty, so they name only a key played on the input shown.
        """
        view_model = self.view_model
        if not view_model.available:
            return

        dpg_configure_item(TAG_SETTINGS_MIDI_COMBO_PORT, items=list(view_model.port_items(self._no_input)))
        dpg_set_value(TAG_SETTINGS_MIDI_COMBO_PORT, view_model.port_item(self._no_input))
        dpg_set_value(TAG_SETTINGS_MIDI_CHECKBOX_VELOCITY, view_model.velocity_sets_volume)
        refusal = view_model.refusal
        message = self._language_manager["settings.midi.message.play_a_key"] if refusal is None else refusal
        dpg_set_value(TAG_SETTINGS_MIDI_TEXT_MESSAGE, message)
        dpg_set_value(TAG_SETTINGS_MIDI_TEXT_LAST_KEY, "")
        dpg_set_value(TAG_SETTINGS_MIDI_TEXT_VELOCITY, "")

    def _on_port_changed(self, _sender: Sender, app_data: str) -> None:
        self.call(self.on_port_changed, None if app_data == self._no_input else app_data)

    def _request_refresh(self) -> None:
        self.call(self.on_refresh)

    def _request_commit(self) -> None:
        """Reports the velocity setting as the dialog shows it, read while the checkbox still stands."""
        velocity_sets_volume = (
            bool(dpg.get_value(TAG_SETTINGS_MIDI_CHECKBOX_VELOCITY))
            if self.view_model.available
            else self.view_model.velocity_sets_volume
        )
        self.call(self.on_commit, velocity_sets_volume)

    def _request_cancel(self) -> None:
        self.call(self.on_cancel)
