from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.conversion import MIN_CHANNEL_CAP
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_CHANNELS,
    SUF_CHECKBOX,
    SUF_GROUP,
    SUF_TEXT,
    TAG_GLOBAL_THEME_DANGER_BUTTON,
    TAG_GLOBAL_THEME_PANEL_EMPHASIS,
    TAG_GLOBAL_THEME_PRIMARY_BUTTON,
)
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_STEM,
    TAG_MAIN_CONVERTER_BUTTON_ACTION,
    TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE,
    TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
    TAG_MAIN_CONVERTER_GROUP,
    TAG_MAIN_CONVERTER_GROUP_CONTROLS,
    TAG_MAIN_CONVERTER_GROUP_CONVERT,
    TAG_MAIN_CONVERTER_GROUP_STEMS,
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
    TAG_MAIN_CONVERTER_WINDOW_SUMMARY,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIDestinationPathText, GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_item,
    dpg_set_item_callback,
    dpg_set_value,
)
from sampletones_application.utils.gui.tooltip import attach_disabled_tooltip
from sampletones_application.view_model.main.converter import (
    ConverterAction,
    ConverterViewModel,
    StemSourceRow,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import PathCallback, VoidCallback


class GUIConverterPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: ConverterLayout,
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

        self._layout = layout
        self._path_colors = path_colors
        self._msg_path = language_manager["global.status.message.path"]
        self._msg_destination = language_manager["global.status.message.destination"]
        self._msg_status_convert = language_manager["main.converter.message.status_convert"]
        self._status_action_message = self._msg_status_convert
        self._hierarchy_labels: Dict[HierarchyMode, str] = {
            HierarchyMode.ROUND_ROBIN: language_manager["main.converter.label.hierarchy_round_robin"],
            HierarchyMode.STRICT: language_manager["main.converter.label.hierarchy_strict"],
        }
        self._hierarchy_modes: List[HierarchyMode] = list(self._hierarchy_labels)
        self._stem_rows: List[Path] = []

        super().__init__(
            tag=TAG_MAIN_CONVERTER_PANEL,
            height=layout.height,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._language_manager["main.converter.label.section"],
            glyph=self._glyphs.headers.converter,
            width=self.width,
            card_theme=TAG_GLOBAL_THEME_PANEL_EMPHASIS,
        ):
            self._create_action_button()
            dpg.add_separator()
            self._create_controls()
            self._create_stems_list()
            self._create_summary()
            self._create_conversion_status()

    def is_visible(self) -> bool:
        return bool(dpg.get_item_configuration(self.tag)["show"])

    def update_view(self, view_model: ConverterViewModel) -> None:
        self._update_visibility(view_model)
        self._update_status(view_model)
        self._update_paths(view_model)
        self._update_controls(view_model)
        self._update_setup(view_model)

    def _update_visibility(self, view_model: ConverterViewModel) -> None:
        dpg.configure_item(TAG_MAIN_CONVERTER_GROUP, show=view_model.subpanel_visible)
        dpg_configure_item(TAG_MAIN_CONVERTER_WINDOW_SUMMARY, show=not view_model.subpanel_visible)
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
        with dpg.group(horizontal=True, tag=TAG_MAIN_CONVERTER_GROUP_CONTROLS):
            dpg.add_checkbox(
                label=self._language_manager["main.converter.label.stems_mode"],
                tag=TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE,
                callback=self._on_stems_mode_toggled,
            )
            dpg.add_input_int(
                label=self._language_manager["main.converter.label.channel_cap"],
                tag=TAG_MAIN_CONVERTER_INPUT_CHANNEL_CAP,
                width=self._layout.cap_input_width,
                min_value=MIN_CHANNEL_CAP,
                min_clamped=True,
                max_clamped=True,
                step=1,
                step_fast=1,
                callback=self._on_channel_cap_changed,
            )

        with dpg.group(horizontal=True):
            dpg.add_combo(
                items=list(self._hierarchy_labels.values()),
                label=self._language_manager["main.converter.label.hierarchy_mode"],
                tag=TAG_MAIN_CONVERTER_COMBO_HIERARCHY_MODE,
                width=self._layout.hierarchy_combo_width,
                default_value=self._hierarchy_labels[HierarchyMode.ROUND_ROBIN],
                callback=self._on_hierarchy_mode_changed,
            )

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
            with dpg.tooltip(tag, tag=tooltip_tag):
                dpg.add_text(message)

    def _create_stems_list(self) -> None:
        """The recordings gathered so far, one row each, scrolling when the list outgrows its space."""
        with dpg.child_window(
            tag=TAG_MAIN_CONVERTER_WINDOW_STEMS,
            width=-1,
            height=self._layout.stems_list_height,
            border=False,
            show=False,
        ):
            hint = dpg.add_text(
                self._language_manager["main.converter.message.stems_empty_hint"],
                tag=TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
                wrap=0,
            )
            FontRegistry.bind_to_item(hint, Font.REGULAR_SMALL)
            dpg.add_group(tag=TAG_MAIN_CONVERTER_GROUP_STEMS)

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
        dpg_configure_item(TAG_MAIN_CONVERTER_CHECKBOX_STEMS_MODE, enabled=not view_model.is_active)
        self._update_stems_list(view_model)

    def _update_stems_list(self, view_model: ConverterViewModel) -> None:
        dpg_configure_item(
            TAG_MAIN_CONVERTER_WINDOW_STEMS,
            show=view_model.stems_mode and not view_model.subpanel_visible,
        )
        dpg_configure_item(
            TAG_MAIN_CONVERTER_TEXT_STEMS_HINT,
            show=view_model.source_count == 0,
        )
        self._sync_stem_rows(view_model)
        for row in view_model.stem_sources:
            self._render_stem_row(row, view_model)

        self.set_expanded_height(self._card_height(view_model))

    def _card_height(self, view_model: ConverterViewModel) -> int:
        """The room the card takes: its own, plus the list's where the list is on show."""
        if view_model.stems_mode and not view_model.subpanel_visible:
            return self._layout.height + self._layout.stems_list_height

        return self._layout.height

    def _sync_stem_rows(self, view_model: ConverterViewModel) -> None:
        """Rebuilds the rows when the recordings change, keeps them otherwise."""
        listed = [row.path for row in view_model.stem_sources]
        if listed == self._stem_rows:
            return

        for path in self._stem_rows:
            dpg_delete_item(self._row_tag(path, SUF_GROUP))

        self._stem_rows = listed
        for row in view_model.stem_sources:
            self._create_stem_row(row, view_model)

    def _create_stem_row(self, row: StemSourceRow, view_model: ConverterViewModel) -> None:
        with dpg.group(
            horizontal=True,
            tag=self._row_tag(row.path, SUF_GROUP),
            parent=TAG_MAIN_CONVERTER_GROUP_STEMS,
        ):
            name = dpg.add_text(row.name, tag=self._row_tag(row.path, SUF_TEXT))
            FontRegistry.bind_to_item(name, Font.REGULAR_SMALL)
            with dpg.tooltip(name):
                dpg.add_text(str(row.path))

            for channel_name in ChannelName.items():
                dpg.add_checkbox(
                    label=channel_label(self._language_manager, channel_name),
                    tag=self._channel_tag(row.path, channel_name),
                    show=channel_name in view_model.enabled_channels,
                    default_value=channel_name in row.channels,
                    user_data=row.path,
                    callback=self._on_source_channels_changed,
                )

            remove = dpg.add_button(
                label=self._language_manager["main.converter.label.stem_remove"],
                tag=self._row_tag(row.path, SUF_BUTTON),
                width=self._layout.remove_button_width,
                user_data=row.path,
                callback=self._on_source_removed,
            )
            self._status_bar.bind_to_item(
                remove,
                self._language_manager["main.converter.message.status_stem_remove"],
            )

    def _render_stem_row(self, row: StemSourceRow, view_model: ConverterViewModel) -> None:
        for channel_name in ChannelName.items():
            tag = self._channel_tag(row.path, channel_name)
            dpg_configure_item(
                tag,
                show=channel_name in view_model.enabled_channels,
                enabled=not view_model.is_active,
            )
            dpg_set_value(tag, channel_name in row.channels)

        dpg_configure_item(self._row_tag(row.path, SUF_BUTTON), enabled=not view_model.is_active)

    def _on_stems_mode_toggled(self, _sender: Sender, value: bool) -> None:
        self.call(self.on_stems_mode_changed, value)

    def _on_channel_cap_changed(self, _sender: Sender, value: int) -> None:
        self.call(self.on_channel_cap_changed, value)

    def _on_hierarchy_mode_changed(self, _sender: Sender, value: str) -> None:
        for hierarchy_mode, label in self._hierarchy_labels.items():
            if label == value:
                self.call(self.on_hierarchy_mode_changed, hierarchy_mode)
                return

    def _on_source_channels_changed(self, _sender: Sender, _value: bool, user_data: Path) -> None:
        channels = frozenset(
            channel_name
            for channel_name in ChannelName.items()
            if dpg.get_value(self._channel_tag(user_data, channel_name))
        )
        self.call(self.on_source_channels_changed, user_data, channels)

    def _on_source_removed(self, _sender: Sender, _app_data: Any, user_data: Path) -> None:
        self.call(self.on_source_removed, user_data)

    @staticmethod
    def _row_tag(path: Path, suffix: str) -> str:
        return compose_tag(PRE_MAIN_CONVERTER_STEM, str(path), suffix)

    @classmethod
    def _channel_tag(cls, path: Path, channel_name: ChannelName) -> str:
        return compose_tag(
            PRE_MAIN_CONVERTER_STEM,
            str(path),
            SUF_CHANNELS,
            compose_tag(channel_name, SUF_CHECKBOX),
        )

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
        with dpg.child_window(
            tag=TAG_MAIN_CONVERTER_WINDOW_SUMMARY,
            width=-1,
            height=-1,
            border=False,
        ):
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
