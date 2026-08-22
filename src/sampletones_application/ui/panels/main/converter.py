from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.main import ConverterStemMoveElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.conversion import MIN_CHANNEL_CAP
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.general.inputs import InputsLayout
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_REGISTRY,
    TAG_GLOBAL_THEME_DANGER_BUTTON,
    TAG_GLOBAL_THEME_PANEL_EMPHASIS,
    TAG_GLOBAL_THEME_PRIMARY_BUTTON,
)
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_STEMS,
    TAG_MAIN_CONVERTER_BUTTON_ACTION,
    TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE,
    TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
    TAG_MAIN_CONVERTER_GROUP,
    TAG_MAIN_CONVERTER_GROUP_CONTROLS,
    TAG_MAIN_CONVERTER_GROUP_CONVERT,
    TAG_MAIN_CONVERTER_GROUP_SUMMARY,
    TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
    TAG_MAIN_CONVERTER_PROGRESS,
    TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
    TAG_MAIN_CONVERTER_TEXT_STATUS,
    TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
    TAG_MAIN_CONVERTER_TEXT_SUMMARY_HINT,
    TAG_MAIN_CONVERTER_TOOLTIP_CHANNEL_CAP,
    TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
    TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE,
    TAG_MAIN_CONVERTER_TOOLTIP_STEMS_MODE,
    TAG_MAIN_CONVERTER_WINDOW_STEMS,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.context_menu import add_path_menu_items, context_menu
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIDestinationPathText, GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_set_item_callback,
    dpg_set_value,
)
from sampletones_application.utils.gui.tooltip import (
    attach_disabled_tooltip,
    set_tooltip_visible,
    show_tooltip,
)
from sampletones_application.utils.gui.widgets import clamp_widget_value
from sampletones_application.view_model.main.converter import (
    ConverterAction,
    ConverterViewModel,
)
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import PathCallback, VoidCallback

PathOffsetCallback = Callable[[Path, int], None]

LEVEL_ABOVE: int = -1
LEVEL_BELOW: int = 1
POSITION_EARLIER: int = -1
POSITION_LATER: int = 1


class GUIConverterPanel(GUIPanel):
    """The card a conversion is set up on: what it converts, how, and what it is doing.

    In stems mode the card lists the recordings being gathered under the levels they pick on.
    A row is dragged by its handle onto another row to share that row's level, or onto the gap
    between two levels to open one of its own; the row's menu names the same moves in words and
    offers the recording's own filesystem actions.
    """

    def __init__(
        self,
        *,
        layout: ConverterLayout,
        stems_layout: StemsListLayout,
        inputs: InputsLayout,
        path_colors: PathColors,
        initial_collapsed: bool = False,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIDestinationPathText] = None
        self._status_bar = status_bar
        self._action_button: Optional[GUIButton] = None
        self._theme_convert: Optional[Theme] = None
        self._theme_cancel: Optional[Theme] = None

        self.on_convert_requested: Optional[VoidCallback] = None
        self.on_cancel_requested: Optional[VoidCallback] = None
        self.on_stems_mode_changed: Optional[Callable[[bool], None]] = None
        self.on_channel_cap_changed: Optional[Callable[[int], None]] = None
        self.on_hierarchy_mode_changed: Optional[Callable[[HierarchyMode], None]] = None
        self.on_source_channels_changed: Optional[Callable[[Path, FrozenSet[ChannelName]], None]] = None
        self.on_source_removed: Optional[PathCallback] = None
        self.on_source_moved: Optional[PathOffsetCallback] = None
        self.on_source_level_joined: Optional[PathOffsetCallback] = None
        self.on_source_isolated: Optional[PathCallback] = None
        self.on_source_dropped_on_source: Optional[Callable[[Path, Path], None]] = None
        self.on_source_dropped_on_level: Optional[Callable[[Path, int], None]] = None

        self._layout = layout
        self._input_width = inputs.default_width
        self._label_width = inputs.label_width
        self._path_colors = path_colors
        self._msg_path = language_manager["global.status.message.path"]
        self._msg_destination = language_manager["global.status.message.destination"]
        self._msg_status_convert = language_manager["main.converter.message.status_convert"]
        self._status_action_message = self._msg_status_convert
        self._hierarchy_labels: Dict[HierarchyMode, str] = {
            HierarchyMode.ROUND_ROBIN: language_manager["main.converter.label.hierarchy_round_robin"],
            HierarchyMode.STRICT: language_manager["main.converter.label.hierarchy_strict"],
        }
        self._settings_handler_tag = compose_tag(TAG_MAIN_CONVERTER_PANEL, SUF_HANDLER_REGISTRY)
        self._stems_list = GUIStemsList(
            prefix=PRE_MAIN_CONVERTER_STEMS,
            layout=stems_layout,
            language_manager=language_manager,
            status_bar=status_bar,
            draggable=True,
            removable=True,
        )

        super().__init__(tag=TAG_MAIN_CONVERTER_PANEL)
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed, auto_height=True)

    def create_panel(self, parent: str) -> None:
        self._create_handlers()
        with self._collapsible_card(
            parent,
            self._language_manager["main.converter.label.section"],
            glyph=self._glyphs.headers.converter,
            width=self.width,
            no_scrollbar=True,
            card_theme=TAG_GLOBAL_THEME_PANEL_EMPHASIS,
        ):
            self._create_action_button()
            dpg.add_separator()
            self._create_controls()
            self._create_stems_list()
            self._create_summary()
            self._create_conversion_status()

    @property
    def stems_list(self) -> GUIStemsList:
        """The list the gathered recordings are drawn in, which is what addresses their widgets."""
        return self._stems_list

    def is_visible(self) -> bool:
        return bool(dpg.get_item_configuration(self.tag)["show"])

    def update_view(self, view_model: ConverterViewModel) -> None:
        self._update_status(view_model)
        self._update_paths(view_model)
        self._update_controls(view_model)
        self._update_setup(view_model)
        self._update_visibility(view_model)

    def _create_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._settings_handler_tag):
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_channel_cap_edited)

    def _update_visibility(self, view_model: ConverterViewModel) -> None:
        dpg_configure_item(TAG_MAIN_CONVERTER_GROUP, show=view_model.subpanel_visible)
        dpg_configure_item(TAG_MAIN_CONVERTER_TEXT_SUMMARY_HINT, show=not view_model.has_input)
        dpg_configure_item(TAG_MAIN_CONVERTER_GROUP_SUMMARY, show=view_model.has_input)

    def _update_status(self, view_model: ConverterViewModel) -> None:
        dpg_set_value(TAG_MAIN_CONVERTER_TEXT_STATUS, view_model.status_text)
        dpg_set_value(TAG_MAIN_CONVERTER_PROGRESS, view_model.progress)
        dpg_configure_item(TAG_MAIN_CONVERTER_PROGRESS, overlay=view_model.progress_overlay)

    def _update_paths(self, view_model: ConverterViewModel) -> None:
        if self.input_path_text is not None and view_model.input_path is not None:
            self.input_path_text.set_path(view_model.input_path)
        if self.output_path_text is not None and view_model.output_path is not None:
            self.output_path_text.set_path(view_model.output_path)

    def _update_controls(self, view_model: ConverterViewModel) -> None:
        match view_model.primary_action:
            case ConverterAction.CANCEL:
                callback: VoidCallback = self._on_cancel_clicked
                theme = self._theme_cancel
                self._status_action_message = self._language_manager["main.converter.message.status_cancel"]
            case ConverterAction.CONVERT:
                callback = self._on_convert_clicked
                theme = self._theme_convert
                self._status_action_message = self._msg_status_convert

        dpg_configure_item(
            TAG_MAIN_CONVERTER_BUTTON_ACTION,
            label=view_model.action_label,
            enabled=view_model.primary_action_enabled,
        )
        dpg_set_item_callback(TAG_MAIN_CONVERTER_BUTTON_ACTION, callback)
        if self._action_button is not None and theme is not None:
            self._action_button.set_theme(theme)
        dpg_configure_item(
            TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
            show=view_model.other_operation_active and view_model.primary_action == ConverterAction.CONVERT,
        )

    def _create_controls(self) -> None:
        """The row of choices every conversion carries: stems mode, the cap, and the picking order."""
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_CONTROLS):
            dpg.add_checkbox(
                label=self._language_manager["main.converter.label.stems_mode"],
                tag=TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE,
                callback=self._on_stems_mode_toggled,
            )
            with labeled_field(self._language_manager["main.converter.label.channel_cap"], self._label_width):
                cap_input = dpg.add_input_int(
                    tag=TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
                    width=self._input_width,
                    min_value=MIN_CHANNEL_CAP,
                    min_clamped=True,
                    max_clamped=True,
                    default_value=len(ChannelName),
                    callback=self._on_channel_cap_edited,
                )
                FontRegistry.bind_to_item(cap_input, Font.MONO)

            with labeled_field(self._language_manager["main.converter.label.hierarchy_mode"], self._label_width):
                dpg.add_combo(
                    items=list(self._hierarchy_labels.values()),
                    tag=TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
                    width=self._input_width,
                    default_value=self._hierarchy_labels[HierarchyMode.ROUND_ROBIN],
                    callback=self._on_hierarchy_mode_changed,
                )

        dpg.bind_item_handler_registry(TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP, self._settings_handler_tag)
        self._attach_control_tooltips()
        self._status_bar.bind_to_item(
            TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE,
            self._language_manager["main.converter.message.status_stems_mode"],
        )

    def _attach_control_tooltips(self) -> None:
        for tag, message, tooltip_tag in (
            (
                TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE,
                self._language_manager["main.converter.message.stems_mode_tooltip"],
                TAG_MAIN_CONVERTER_TOOLTIP_STEMS_MODE,
            ),
            (
                TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
                self._language_manager["main.converter.message.channel_cap_tooltip"],
                TAG_MAIN_CONVERTER_TOOLTIP_CHANNEL_CAP,
            ),
            (
                TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
                self._language_manager["main.converter.message.hierarchy_mode_tooltip"],
                TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE,
            ),
        ):
            show_tooltip(tag, message, tag=tooltip_tag)

    def _create_stems_list(self) -> None:
        """The recordings gathered so far, under the levels they pick on."""
        with dpg.group(tag=TAG_MAIN_CONVERTER_WINDOW_STEMS, show=False):
            hint = dpg.add_text(
                self._language_manager["main.converter.message.stems_empty_hint"],
                tag=TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
                wrap=0,
            )
            FontRegistry.bind_to_item(hint, Font.REGULAR_SMALL)
            self._stems_list.create(TAG_MAIN_CONVERTER_WINDOW_STEMS)

        self._stems_list.on_channels_changed = self._on_source_channels_changed
        self._stems_list.on_remove_requested = self._on_source_removed
        self._stems_list.on_menu_requested = self._show_row_menu
        self._stems_list.on_dropped_on_row = self._on_dropped_on_source
        self._stems_list.on_dropped_on_level = self._on_dropped_on_level

    def _update_setup(self, view_model: ConverterViewModel) -> None:
        dpg_set_value(TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE, view_model.stems_mode)
        dpg_configure_item(
            TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
            max_value=view_model.max_channel_cap,
            enabled=not view_model.is_active,
        )
        dpg_set_value(TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP, view_model.channel_cap)
        dpg_set_value(
            TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
            self._hierarchy_labels[view_model.hierarchy_mode],
        )
        dpg_configure_item(TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE, show=view_model.stems_mode)
        set_tooltip_visible(TAG_MAIN_CONVERTER_TOOLTIP_HIERARCHY_MODE, view_model.stems_mode)
        dpg_configure_item(TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE, enabled=not view_model.is_active)
        self._update_stems_list(view_model)

    def _update_stems_list(self, view_model: ConverterViewModel) -> None:
        dpg_configure_item(TAG_MAIN_CONVERTER_WINDOW_STEMS, show=view_model.stems_mode)
        dpg_configure_item(TAG_MAIN_CONVERTER_TEXT_STEMS_HINT, show=view_model.source_count == 0)
        self._stems_list.update_view(view_model.stems_list)

    def _on_stems_mode_toggled(self, _sender: Sender, value: bool) -> None:
        self.call(self.on_stems_mode_changed, value)

    def _on_channel_cap_edited(self, _sender: Sender, _app_data: Any) -> None:
        self.call(self.on_channel_cap_changed, int(clamp_widget_value(TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP)))

    def _on_hierarchy_mode_changed(self, _sender: Sender, value: str) -> None:
        for hierarchy_mode, label in self._hierarchy_labels.items():
            if label == value:
                self.call(self.on_hierarchy_mode_changed, hierarchy_mode)
                return

    def _on_source_channels_changed(self, key: str, channels: FrozenSet[ChannelName]) -> None:
        self.call(self.on_source_channels_changed, Path(key), channels)

    def _on_source_removed(self, key: str) -> None:
        self.call(self.on_source_removed, Path(key))

    def _on_dropped_on_source(self, key: str, target_key: str) -> None:
        self.call(self.on_source_dropped_on_source, Path(key), Path(target_key))

    def _on_dropped_on_level(self, key: str, position: int) -> None:
        self.call(self.on_source_dropped_on_level, Path(key), position)

    def _show_row_menu(self, key: str) -> None:
        """Names the moves the row can make, greying out the ones that would change nothing,
        and offers the recording's own filesystem actions below them."""
        row = self._stems_list.row(key)
        if row is None:
            return

        with context_menu():
            header = dpg.add_text(row.name)
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            for element, enabled, callback in self._row_moves(row):
                dpg.add_menu_item(
                    label=self._label(element),
                    enabled=enabled,
                    callback=callback,
                )

            add_path_menu_items(self._language_manager, row.path)

    def _row_moves(self, row: StemRowViewModel) -> List[Tuple[ConverterStemMoveElements, bool, VoidCallback]]:
        path = row.path
        return [
            (
                ConverterStemMoveElements.CONTEXT_MOVE_UP,
                not row.is_first_on_level,
                lambda: self.call(self.on_source_moved, path, POSITION_EARLIER),
            ),
            (
                ConverterStemMoveElements.CONTEXT_MOVE_DOWN,
                not row.is_last_on_level,
                lambda: self.call(self.on_source_moved, path, POSITION_LATER),
            ),
            (
                ConverterStemMoveElements.CONTEXT_JOIN_ABOVE,
                row.has_level_above,
                lambda: self.call(self.on_source_level_joined, path, LEVEL_ABOVE),
            ),
            (
                ConverterStemMoveElements.CONTEXT_JOIN_BELOW,
                row.has_level_below,
                lambda: self.call(self.on_source_level_joined, path, LEVEL_BELOW),
            ),
            (
                ConverterStemMoveElements.CONTEXT_ISOLATE,
                not row.alone_on_level,
                lambda: self.call(self.on_source_isolated, path),
            ),
            (
                ConverterStemMoveElements.CONTEXT_REMOVE_STEM,
                True,
                lambda: self.call(self.on_source_removed, path),
            ),
        ]

    def _label(self, element: ConverterStemMoveElements) -> str:
        return self._language_manager[Page.MAIN, Panel.CONVERTER, TextType.LABEL, element]

    def _create_action_button(self) -> None:
        self._theme_convert = ThemeRegistry.get(TAG_GLOBAL_THEME_PRIMARY_BUTTON)
        self._theme_cancel = ThemeRegistry.get(TAG_GLOBAL_THEME_DANGER_BUTTON)
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_CONVERT):
            self._action_button = GUIButton(
                label=self._language_manager["main.converter.label.convert_sample_button"],
                tag=TAG_MAIN_CONVERTER_BUTTON_ACTION,
                width=self._layout.width,
                height=self._layout.button_height,
                font=Font.BOLD_LARGE,
                enabled=False,
                callback=self._on_convert_clicked,
                theme=self._theme_convert,
            )
        attach_disabled_tooltip(
            TAG_MAIN_CONVERTER_GROUP_CONVERT,
            self._language_manager["global.dialog.message.operation_in_progress"],
            tag=TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
        )
        self._status_bar.bind_to_item(
            TAG_MAIN_CONVERTER_BUTTON_ACTION,
            self._action_status_message,
        )

    def _action_status_message(self, *_args: Any, **_kwargs: Any) -> str:
        return self._status_action_message

    def _create_summary(self) -> None:
        dpg.add_separator()
        hint = dpg.add_text(
            self._language_manager["main.converter.message.status_empty_hint"],
            tag=TAG_MAIN_CONVERTER_TEXT_SUMMARY_HINT,
        )
        FontRegistry.bind_to_item(hint, Font.REGULAR_SMALL)
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_SUMMARY, show=False):
            self.input_path_text = GUIPathText(
                path=None,
                prefix=self._language_manager["main.converter.message.status_input_label"],
                tag=TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
                parent=TAG_MAIN_CONVERTER_GROUP_SUMMARY,
                color=self._path_colors.default,
                hover_color=self._path_colors.hover,
                status_message=self._msg_path,
                font=Font.REGULAR_SMALL,
                status_bar=self._status_bar,
            )
            self.output_path_text = GUIDestinationPathText(
                path=None,
                prefix=self._language_manager["main.converter.message.status_output_label"],
                tag=TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
                parent=TAG_MAIN_CONVERTER_GROUP_SUMMARY,
                color=self._path_colors.default,
                hover_color=self._path_colors.hover,
                status_message=self._msg_destination,
                font=Font.REGULAR_SMALL,
                status_bar=self._status_bar,
            )

    def _create_conversion_status(self) -> None:
        with dpg.group(
            tag=TAG_MAIN_CONVERTER_GROUP,
            show=False,
        ):
            dpg.add_text(
                self._language_manager["main.converter.message.status_waiting"],
                tag=TAG_MAIN_CONVERTER_TEXT_STATUS,
                parent=TAG_MAIN_CONVERTER_GROUP,
            )
            FontRegistry.bind_to_item(
                TAG_MAIN_CONVERTER_TEXT_STATUS,
                Font.MONO_SMALL,
            )
            dpg.add_progress_bar(
                tag=TAG_MAIN_CONVERTER_PROGRESS,
                parent=TAG_MAIN_CONVERTER_GROUP,
                default_value=0.0,
                width=-1,
                overlay="0%",
            )
            FontRegistry.bind_to_item(TAG_MAIN_CONVERTER_PROGRESS, Font.MONO)

    def _on_convert_clicked(self) -> None:
        self.call(self.on_convert_requested)

    def _on_cancel_clicked(self) -> None:
        self.call(self.on_cancel_requested)
