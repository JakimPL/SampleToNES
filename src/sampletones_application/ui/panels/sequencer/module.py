from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import StatusElements
from sampletones_application.categories.elements.sequencer import (
    SequencerModuleElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_MODULE_GROUP_OPTIONS,
    TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY,
    TAG_SEQUENCER_MODULE_INPUT_ROWS,
    TAG_SEQUENCER_MODULE_INPUT_SPEED,
    TAG_SEQUENCER_MODULE_INPUT_TEMPO,
    TAG_SEQUENCER_MODULE_PANEL,
)
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)
from sampletones_core.constants.general import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY
from sampletones_shared.constants.project import (
    MAX_ROWS_PER_PATTERN,
    MIN_ROWS_PER_PATTERN,
)
from sampletones_shared.types.application import Sender


class GUISequencerModulePanel(GUIPanel):
    def __init__(
        self,
        initial_settings: SequencerSettingsViewModel,
        *,
        layout: SequencerLayout,
        input_width: int,
        label_width: int,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        shortcut_manager: ShortcutManager,
    ) -> None:
        self._initial_settings = initial_settings
        self._layout = layout
        self._input_width = input_width
        self._label_width = label_width
        self._status_bar = status_bar
        self._shortcut_manager = shortcut_manager
        self._nes_frequency_handler_tag = f"{TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY}{SUF_HANDLER_REGISTRY}"
        self._rows_handler_tag = f"{TAG_SEQUENCER_MODULE_INPUT_ROWS}{SUF_HANDLER_REGISTRY}"

        self.on_nes_frequency: Optional[Callable[[int], None]] = None
        self.on_rows_per_pattern: Optional[Callable[[int], None]] = None
        self.on_tempo: Optional[Callable[[int], None]] = None
        self.on_speed: Optional[Callable[[int], None]] = None

        self._lbl_module_options = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.MODULE_OPTIONS,
        ]
        self._lbl_nes_frequency = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.NES_FREQUENCY,
        ]
        self._lbl_rows = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.ROWS,
        ]
        self._tpl_rows_tooltip = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.TOOLTIP,
            SequencerModuleElements.ROWS,
        ]
        self._lbl_tempo = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.TEMPO,
        ]
        self._lbl_speed = language_manager[
            Page.SEQUENCER,
            Panel.MODULE,
            TextType.LABEL,
            SequencerModuleElements.SPEED,
        ]
        self._msg_status_input = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.INPUT,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_MODULE_PANEL,
        )

    def create_panel(self, parent: str) -> None:
        with card(parent, self.tag):
            self._create_section_header(
                self._lbl_module_options,
                glyph=self._glyphs.headers.settings,
            )
            self._create_module_options()

    def _create_module_options(self) -> None:
        settings = self._initial_settings
        with dpg.group(tag=TAG_SEQUENCER_MODULE_GROUP_OPTIONS):
            with labeled_field(self._lbl_nes_frequency, self._label_width):
                dpg.add_input_int(
                    default_value=settings.nes_frequency,
                    tag=TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY,
                    min_value=MIN_NES_FREQUENCY,
                    max_value=MAX_NES_FREQUENCY,
                    min_clamped=True,
                    max_clamped=True,
                    width=self._input_width,
                )
            with labeled_field(self._lbl_rows, self._label_width):
                dpg.add_input_int(
                    default_value=settings.rows_per_pattern,
                    tag=TAG_SEQUENCER_MODULE_INPUT_ROWS,
                    min_value=MIN_ROWS_PER_PATTERN,
                    max_value=MAX_ROWS_PER_PATTERN,
                    min_clamped=True,
                    max_clamped=True,
                    width=self._input_width,
                )
            with labeled_field(self._lbl_tempo, self._label_width):
                dpg.add_input_int(
                    default_value=settings.tempo,
                    tag=TAG_SEQUENCER_MODULE_INPUT_TEMPO,
                    min_value=self._layout.tempo.min,
                    max_value=self._layout.tempo.max,
                    min_clamped=True,
                    max_clamped=True,
                    width=self._input_width,
                    callback=self._on_tempo_input,
                )
            with labeled_field(self._lbl_speed, self._label_width):
                dpg.add_input_int(
                    default_value=settings.speed,
                    tag=TAG_SEQUENCER_MODULE_INPUT_SPEED,
                    min_value=self._layout.speed.min,
                    max_value=self._layout.speed.max,
                    min_clamped=True,
                    max_clamped=True,
                    width=self._input_width,
                    callback=self._on_speed_input,
                )

        for tag in (
            TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY,
            TAG_SEQUENCER_MODULE_INPUT_ROWS,
            TAG_SEQUENCER_MODULE_INPUT_TEMPO,
            TAG_SEQUENCER_MODULE_INPUT_SPEED,
        ):
            FontRegistry.bind_to_item(tag, Font.MONO)

        self._commit_on_finish(
            TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY,
            self._nes_frequency_handler_tag,
            self._on_nes_frequency_input,
        )
        self._commit_on_finish(
            TAG_SEQUENCER_MODULE_INPUT_ROWS,
            self._rows_handler_tag,
            self._on_rows_per_pattern_input,
        )
        self._shortcut_manager.setup_input_focus_handlers(TAG_SEQUENCER_MODULE_INPUT_TEMPO)
        self._shortcut_manager.setup_input_focus_handlers(TAG_SEQUENCER_MODULE_INPUT_SPEED)
        show_tooltip(TAG_SEQUENCER_MODULE_INPUT_ROWS, self._tpl_rows_tooltip)
        self._status_bar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY, self._msg_status_input)
        self._status_bar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_ROWS, self._msg_status_input)
        self._status_bar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_TEMPO, self._msg_status_input)
        self._status_bar.bind_to_item(TAG_SEQUENCER_MODULE_INPUT_SPEED, self._msg_status_input)

    def update_settings(self, view_model: SequencerSettingsViewModel) -> None:
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY, view_model.nes_frequency)
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_ROWS, view_model.rows_per_pattern)
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_TEMPO, view_model.tempo)
        dpg.set_value(TAG_SEQUENCER_MODULE_INPUT_SPEED, view_model.speed)

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_MODULE_GROUP_OPTIONS, enabled=enabled)

    def _commit_on_finish(self, input_tag: str, handler_tag: str, callback: Callable[[Sender, int], None]) -> None:
        """Commits a field only when editing finishes (focus lost or Enter pressed).

        Used for the fields whose change rebuilds or re-times the song — NES frequency and rows
        per pattern. Committing per keystroke or [-]/[+] step would resize the grid mid-edit (and,
        for the frequency, prompt repeatedly); ``deactivated_after_edit`` collapses a burst of edits
        into a single commit.
        """
        with dpg.item_handler_registry(tag=handler_tag):
            dpg.add_item_deactivated_after_edit_handler(callback=callback)

        self._shortcut_manager.attach_focus_tracking(handler_tag)
        dpg.bind_item_handler_registry(input_tag, handler_tag)

    def _on_nes_frequency_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_nes_frequency, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_NES_FREQUENCY)))

    def _on_rows_per_pattern_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_rows_per_pattern, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_ROWS)))

    def _on_tempo_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_tempo, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_TEMPO)))

    def _on_speed_input(self, sender: Sender, app_data: int) -> None:
        self.call(self.on_speed, int(clamp_widget_value(TAG_SEQUENCER_MODULE_INPUT_SPEED)))
