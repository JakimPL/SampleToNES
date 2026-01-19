from typing import Any, Callable, Dict, Optional, Tuple, cast

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.constants.enums import FeatureKey, GeneratorName
from sampletones.constants.general import MAX_PERIOD, MIN_PITCH
from sampletones.exporters import Features
from sampletones.typehints import FeatureValue, Sender, VoidCallback
from sampletones.utils import (
    NAME_TO_PERIOD,
    NAME_TO_PITCH,
    SANITIZED_NAME_TO_PERIOD,
    SANITIZED_NAME_TO_PITCH,
    clamp,
    clamp_period,
    clamp_pitch,
    period_to_name,
    pitch_to_name,
    sanitize_period,
    sanitize_pitch,
)
from sampletones.utils.logger import logger

from ...constants.general import (
    COL_TEXT_DISABLED_DEFAULT,
    DIM_BUTTON_INPUT_INT,
    DIM_BUTTON_WIDTH_COPY,
    MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
    SUF_BUTTON_COPY,
    SUF_DECREMENT,
    SUF_GROUP,
    SUF_HANDLER_REGISTRY,
    SUF_INCREMENT,
    SUF_INPUT,
    SUF_LABEL,
    SUF_PANEL_RIGHT,
    SUF_TABLE,
    SUF_TEXT,
    TAG_TAB_RECONSTRUCTIONS,
    VAL_CHARACTER_BUTTON_DECREMENT,
    VAL_CHARACTER_BUTTON_INCREMENT,
    VAL_DELAY_SCHEDULE,
    VAL_PRIORITY_SCHEDULE,
)
from ...constants.graphs import DIM_BAR_PLOT_HEIGHT, DIM_BAR_PLOT_WIDTH, SUF_GRAPH, SUF_GRAPH_RAW_DATA
from ...constants.reconstructions import (
    DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_BUTTON,
    DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_DISPLAY,
    DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_LABEL,
    LBL_BUTTON_RECONSTRUCTIONS_DETAILS_COPY,
    LBL_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI,
    LBL_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
    LBL_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
    LBL_TEXT_RECONSTRUCTIONS_DETAILS_INITIAL_PERIOD,
    LBL_TEXT_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH,
    LBL_TEXT_RECONSTRUCTIONS_DETAILS_RECONSTRUCTION_DETAILS,
    MSG_STATUS_RECONSTRUCTIONS_DETAILS_BAR,
    MSG_STATUS_RECONSTRUCTIONS_DETAILS_COPY_SEQUENCE,
    MSG_STATUS_RECONSTRUCTIONS_DETAILS_INPUT_PERIOD_VALUE,
    MSG_STATUS_RECONSTRUCTIONS_DETAILS_INPUT_PITCH_VALUE,
    MSG_STATUS_RECONSTRUCTIONS_DETAILS_SEQUENCE,
    SUF_RECONSTRUCTIONS_DETAILS_WINDOW,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_NO_DATA_MESSAGE,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_SEPARATOR,
    TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI,
    TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
    TAG_PANEL_RECONSTRUCTIONS_DETAILS,
    TAG_TAB_BAR_RECONSTRUCTIONS_DETAILS,
    TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
    TPL_TOOLTIP_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH,
    VAL_DELAY_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_CHANGE,
    VAL_TOOLTIP_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_PERIOD_EXAMPLE,
    VAL_TOOLTIP_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_PITCH_EXAMPLE,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.graphs.bar import GUIBarGraph
from ...elements.graphs.utils import extend_y_range
from ...elements.panel import GUIPanel
from ...elements.status import GUIStatusBar
from ...reconstruction.config import FEATURE_DISPLAY_ORDER, FEATURE_PLOT_CONFIGS, FeaturePlotConfig
from ...reconstruction.feature import FeatureData
from ...reconstruction.manager import ReconstructionManager
from ...reconstruction.update import ReconstructionUpdate
from ...themes.default import DefaultTheme
from ...themes.input import InvalidInputTheme
from ...themes.tables.initial_pitch import InitialPitchTableTheme
from ...utils.callbacks.queue import CallbackQueue
from ...utils.clipboard import copy_to_clipboard
from ...utils.dpg import dpg_configure_item, dpg_delete_item, dpg_set_value
from ...utils.shortcuts.manager import ShortcutManager
from ...utils.tooltip import show_tooltip

OnInstrumentExportCallback = Callable[[GeneratorName], None]
OnReconstructionInstrumentUpdatedCallback = Callable[[GeneratorName, Features, FeatureKey, FeatureValue], None]
OnReconstructionInstrumentHoveredCallback = Callable[[Optional[int]], None]


class GUIReconstructionDetailsPanel(GUIPanel):
    def __init__(
        self,
        shortcut_manager: ShortcutManager,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        self.shortcut_manager = shortcut_manager
        self.reconstruction_manager = reconstruction_manager

        self.generator_plots: Dict[GeneratorName, Dict[FeatureKey, GUIBarGraph]] = {}

        self.tab_bar_tag = TAG_TAB_BAR_RECONSTRUCTIONS_DETAILS
        self.no_data_message_tag = f"{self.tab_bar_tag}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_NO_DATA_MESSAGE}"
        self.export_button_separator_tag = f"{self.tab_bar_tag}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_SEPARATOR}"
        self.mouse_item_handler_tag = f"{TAG_PANEL_RECONSTRUCTIONS_DETAILS}{SUF_HANDLER_REGISTRY}"

        self._graphs: Dict[str, GUIBarGraph] = {}

        self.theme = DefaultTheme()
        self.invalid_input_theme = InvalidInputTheme()
        self.initial_pitch_theme = InitialPitchTableTheme()
        self._initial_pitch_change_object: Optional[str] = None
        self._initial_pitch_change_timer: Optional[float] = None

        self._pending_reconstruction_update: Optional[ReconstructionUpdate] = None

        self.on_instrument_export: Optional[OnInstrumentExportCallback] = None
        self.on_instruments_export: Optional[VoidCallback] = None
        self.on_reconstruction_instrument_updated: Optional[OnReconstructionInstrumentUpdatedCallback] = None
        self.on_reconstruction_instrument_hovered: Optional[OnReconstructionInstrumentHoveredCallback] = None

        super().__init__(
            tag=TAG_PANEL_RECONSTRUCTIONS_DETAILS,
            parent=f"{TAG_TAB_RECONSTRUCTIONS}{SUF_PANEL_RIGHT}",
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=False,
        ):
            self._create_section_text()
            self._create_export_button()
            self._create_details_panel()

        self._setup_mouse_event_handler()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_TEXT_RECONSTRUCTIONS_DETAILS_RECONSTRUCTION_DETAILS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
            label=LBL_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
            width=-1,
            callback=self._export_instruments,
            enabled=False,
            show=False,
            font=Font.BOLD,
        )

    def _create_details_panel(self) -> None:
        dpg.add_separator(tag=self.export_button_separator_tag, parent=self.tag, show=False)
        dpg.add_text(
            tag=self.no_data_message_tag,
            parent=self.tag,
            default_value=MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
            show=True,
        )

        dpg.add_text(
            LBL_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
            tag=TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
            parent=self.tag,
            show=False,
        )

        with dpg.tab_bar(tag=self.tab_bar_tag, parent=self.tag, show=False):
            self._create_tabs_for_generators()

    def _get_generator_tab_tag(self, generator_name: GeneratorName) -> str:
        return f"{self.tab_bar_tag}_{generator_name}"

    def _get_window_tag(self, tab_tag: str) -> str:
        return f"{tab_tag}{SUF_RECONSTRUCTIONS_DETAILS_WINDOW}"

    def _get_feature_group_tag(self, generator_name: GeneratorName, feature_key: FeatureKey) -> str:
        return f"{self.tab_bar_tag}_{generator_name}_{feature_key}{SUF_GROUP}"

    def _get_feature_text_group_tag(self, generator_name: GeneratorName, feature_key: FeatureKey) -> str:
        return f"{self.tab_bar_tag}_{generator_name}_{feature_key}{SUF_GRAPH_RAW_DATA}"

    def _get_feature_text_tag(self, text_group_tag: str) -> str:
        return f"{text_group_tag}{SUF_TEXT}"

    def _get_feature_plot_tag(self, generator_name: GeneratorName, feature_key: FeatureKey) -> str:
        return f"{self.tab_bar_tag}_{generator_name}_{feature_key}{SUF_GRAPH}"

    def _setup_mouse_event_handler(self) -> None:
        with dpg.handler_registry(tag=self.mouse_item_handler_tag):
            dpg.add_mouse_move_handler(callback=self._on_mouse_move)

    def _export_instruments(self) -> None:
        self.call(self.on_instruments_export)

    def _handle_export_button_clicked(self, sender: Sender, app_data: Any, user_data: GeneratorName) -> None:
        self.call(self.on_instrument_export, user_data)

    def _create_tabs_for_generators(self) -> None:
        for generator_name in GeneratorName.items():
            self._create_generator_tab(generator_name)

    def _create_generator_tab(self, generator_name: GeneratorName) -> None:
        tab_tag = self._get_generator_tab_tag(generator_name)
        window_tag = self._get_window_tag(tab_tag)

        with dpg.tab(
            label=generator_name,
            tag=tab_tag,
            parent=self.tab_bar_tag,
            show=False,
        ):
            self.generator_plots[generator_name] = {}
            button_tag = f"{TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI}_{tab_tag}"
            GUIButton(
                tag=button_tag,
                parent=tab_tag,
                label=LBL_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI,
                width=-1,
                callback=self._handle_export_button_clicked,
                user_data=generator_name,
            )

            with dpg.child_window(
                tag=window_tag,
                parent=tab_tag,
                no_scroll_with_mouse=True,
            ):
                initial_pitch = MIN_PITCH if generator_name != GeneratorName.NOISE else MAX_PERIOD
                self._add_initial_pitch_display(generator_name, initial_pitch, window_tag)
                for feature_key in FEATURE_DISPLAY_ORDER:
                    self._add_generator_feature_display(
                        generator_name,
                        feature_key,
                        window_tag,
                    )

    def _add_generator_feature_display(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        window_tag: str,
    ) -> None:
        feature_group_tag = self._get_feature_group_tag(generator_name, feature_key)
        with dpg.group(
            tag=feature_group_tag,
            parent=window_tag,
        ):
            dpg.add_separator(parent=window_tag)
            feature_data_array = np.empty(0, dtype=np.int8)
            plot = self._create_feature_display(
                generator_name,
                feature_key,
                feature_data_array,
                feature_group_tag,
            )
            self.generator_plots[generator_name][feature_key] = plot

    def _update_initial_pitch(self, generator_name: GeneratorName, window_tag: str) -> None:
        features = self._get_features(generator_name)
        window_tag = self._get_window_tag(self._get_generator_tab_tag(generator_name))
        initial_pitch = cast(int, features[FeatureKey.INITIAL_PITCH])
        input_tag = f"{window_tag}{SUF_INPUT}"
        value_tag = f"{input_tag}{SUF_TEXT}"

        _, display_value = self._format_initial_pitch(generator_name, initial_pitch)
        dpg_set_value(input_tag, display_value)
        dpg_set_value(value_tag, initial_pitch)

    def _update_generator_plot(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        plots = self.generator_plots.get(generator_name)
        if plots is None:
            return

        plot = plots.get(feature_key)
        if plot is None:
            return

        config = FEATURE_PLOT_CONFIGS[feature_key]
        self._configure_plot_data(
            plot,
            generator_name,
            feature_key,
            config,
            data,
        )

    def _update_raw_data_text(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        text_group_tag = self._get_feature_text_group_tag(generator_name, feature_key)
        raw_data_tag = self._get_feature_text_tag(text_group_tag)
        raw_data_text = self._format_data(data)
        dpg_set_value(raw_data_tag, raw_data_text)

    def update_display(self) -> None:
        feature_data = self.current_features
        clear = feature_data is None
        dpg_configure_item(self.export_button_separator_tag, show=not clear)
        dpg_configure_item(self.no_data_message_tag, show=clear)
        dpg_configure_item(self.tab_bar_tag, show=not clear)
        dpg_configure_item(TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS, show=not clear, enabled=not clear)
        dpg_configure_item(TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS, show=not clear)

        if clear or feature_data is None:
            return

        for generator_name in GeneratorName.items():
            tab_tag = self._get_generator_tab_tag(generator_name)
            if generator_name not in feature_data.generators:
                dpg_configure_item(tab_tag, show=False)
                continue

            dpg_configure_item(tab_tag, show=True)
            generator_features = feature_data.get_generator_features(generator_name)
            if generator_features is None:
                dpg_configure_item(tab_tag, show=False)
                continue

            dpg_configure_item(tab_tag, show=True)
            window_tag = self._get_window_tag(tab_tag)
            self._update_initial_pitch(generator_name, window_tag)
            for key in FEATURE_DISPLAY_ORDER:
                if key == FeatureKey.INITIAL_PITCH:
                    continue

                feature: Optional[np.ndarray] = cast(Optional[np.ndarray], generator_features.get(key))
                if feature is None:
                    feature = np.array([], dtype=np.int8)

                self._update_generator_plot(
                    generator_name,
                    key,
                    feature,
                )

                self._update_raw_data_text(
                    generator_name,
                    key,
                    feature,
                )

    def _format_initial_pitch(self, generator_name: GeneratorName, initial_pitch: int) -> Tuple[str, str]:
        if generator_name == GeneratorName.NOISE:
            label = LBL_TEXT_RECONSTRUCTIONS_DETAILS_INITIAL_PERIOD
            display_value = period_to_name(initial_pitch)
        else:
            label = LBL_TEXT_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH
            display_value = pitch_to_name(initial_pitch)

        return label, display_value

    def _add_initial_pitch_display(self, generator_name: GeneratorName, initial_pitch: int, parent: str) -> None:
        input_label_tag = f"{parent}{SUF_LABEL}"
        input_tag = f"{parent}{SUF_INPUT}"
        value_tag = f"{input_tag}{SUF_TEXT}"
        table_tag = f"{parent}{SUF_TABLE}"
        decrement_button_tag = f"{input_tag}{SUF_DECREMENT}"
        increment_button_tag = f"{input_tag}{SUF_INCREMENT}"

        label, display_value = self._format_initial_pitch(generator_name, initial_pitch)
        with dpg.table(
            tag=table_tag,
            parent=parent,
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            resizable=False,
            width=-1,
            height=0,
        ):
            dpg.add_table_column(
                width=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_LABEL,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_LABEL,
            )
            dpg.add_table_column(
                width=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_DISPLAY,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_DISPLAY,
            )
            dpg.add_table_column(width_stretch=True)
            dpg.add_table_column(
                width=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_BUTTON,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_BUTTON,
            )
            dpg.add_table_column(
                width=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_BUTTON,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_BUTTON,
            )
            with dpg.table_row():
                with dpg.table_cell():
                    dpg.add_text(label, tag=input_label_tag)
                with dpg.table_cell():
                    dpg.add_text(
                        str(initial_pitch),
                        tag=value_tag,
                        color=COL_TEXT_DISABLED_DEFAULT,
                    )
                with dpg.table_cell():
                    dpg.add_input_text(
                        tag=input_tag,
                        default_value=display_value,
                        width=-1,
                        callback=self._validate_and_update_initial_pitch_input,
                        on_enter=False,
                        user_data=(
                            generator_name,
                            input_tag,
                            value_tag,
                        ),
                    )

                with dpg.table_cell():
                    GUIButton(
                        label=VAL_CHARACTER_BUTTON_DECREMENT,
                        tag=decrement_button_tag,
                        width=DIM_BUTTON_INPUT_INT,
                        callback=self._change_initial_pitch,
                        user_data=(
                            generator_name,
                            input_tag,
                            value_tag,
                            -1,
                        ),
                    )

                with dpg.table_cell():
                    GUIButton(
                        label=VAL_CHARACTER_BUTTON_INCREMENT,
                        tag=increment_button_tag,
                        width=DIM_BUTTON_INPUT_INT,
                        callback=self._change_initial_pitch,
                        user_data=(
                            generator_name,
                            input_tag,
                            value_tag,
                            1,
                        ),
                    )

        self.initial_pitch_theme.bind_to_item(table_tag)
        self._create_initial_pitch_tooltip(generator_name, input_tag)
        status_message = (
            MSG_STATUS_RECONSTRUCTIONS_DETAILS_INPUT_PITCH_VALUE
            if generator_name != GeneratorName.NOISE
            else MSG_STATUS_RECONSTRUCTIONS_DETAILS_INPUT_PERIOD_VALUE
        )
        GUIStatusBar.bind_to_item(input_tag, status_message)

        self.shortcut_manager.setup_input_focus_handlers(input_tag)
        self._setup_button_hold_handlers(
            decrement_button_tag,
            increment_button_tag,
            generator_name,
            input_tag,
            value_tag,
        )

    def _setup_button_hold_handlers(
        self,
        decrement_button_tag: str,
        increment_button_tag: str,
        generator_name: GeneratorName,
        input_tag: str,
        value_tag: str,
    ) -> None:
        handler_registry_tag = f"{generator_name}{SUF_HANDLER_REGISTRY}".lower()
        dpg_delete_item(handler_registry_tag)
        with dpg.handler_registry(tag=handler_registry_tag):
            dpg.add_mouse_down_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._on_mouse_down,
                user_data=(
                    decrement_button_tag,
                    increment_button_tag,
                    generator_name,
                    input_tag,
                    value_tag,
                ),
            )
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._on_mouse_release,
            )

    def _on_mouse_down(
        self,
        sender: Sender,
        app_data: Any,
        user_data: Tuple[str, str, GeneratorName, str, str],
    ) -> None:
        button_item = None
        decrement_button_tag, increment_button_tag, generator_name, input_tag, value_tag = user_data
        if not dpg.does_item_exist(decrement_button_tag) or not dpg.does_item_exist(increment_button_tag):
            dpg_delete_item(sender)
            return

        if dpg.is_item_hovered(decrement_button_tag):
            button_item = decrement_button_tag
            change = -1
        elif dpg.is_item_hovered(increment_button_tag):
            button_item = increment_button_tag
            change = 1
        else:
            return

        if self._initial_pitch_change_object != button_item or self._initial_pitch_change_timer is None:
            self._initial_pitch_change_object = button_item
            self._initial_pitch_change_timer = 3 * VAL_DELAY_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_CHANGE
            return

        self._initial_pitch_change_timer -= dpg.get_delta_time()
        assert self._initial_pitch_change_timer is not None
        if self._initial_pitch_change_timer > 0:
            return

        pitch_change_data = (generator_name, input_tag, value_tag, change)
        self._change_initial_pitch(sender, app_data, pitch_change_data)
        self._initial_pitch_change_timer = VAL_DELAY_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_CHANGE

    def _on_mouse_release(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self._initial_pitch_change_timer = None
        self._initial_pitch_change_object = None

    def _on_mouse_move(self, sender: Sender, app_data: Tuple[int, int]) -> None:
        tab = dpg.get_value(self.tab_bar_tag)
        if not tab:
            self.call(self.on_reconstruction_instrument_hovered, None)
            return

        tab_tag = dpg.get_item_alias(tab)
        window_tag = self._get_window_tag(tab_tag)
        if not tab_tag or (not dpg.is_item_hovered(tab_tag) and not dpg.is_item_hovered(window_tag)):
            self.call(self.on_reconstruction_instrument_hovered, None)

    def _create_initial_pitch_tooltip(self, generator_name: GeneratorName, input_tag: str) -> None:
        if generator_name == GeneratorName.NOISE:
            pitch_type = "period"
            example_name = VAL_TOOLTIP_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_PERIOD_EXAMPLE
            example_value = NAME_TO_PERIOD[example_name]
        else:
            pitch_type = "pitch"
            example_name = VAL_TOOLTIP_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_PITCH_EXAMPLE
            example_value = NAME_TO_PITCH[example_name]

        show_tooltip(
            input_tag,
            TPL_TOOLTIP_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH.format(
                pitch_type,
                example_name,
                example_value,
            ),
        )

    def _change_initial_pitch(
        self,
        sender: Sender,
        app_data: int,
        user_data: Tuple[GeneratorName, str, str, int],
    ) -> None:
        if user_data is None:
            return

        generator_name, input_tag, value_tag, change = user_data
        if generator_name == GeneratorName.NOISE:
            current_name = sanitize_period(dpg.get_value(input_tag))
            if current_name not in SANITIZED_NAME_TO_PERIOD:
                return

            value = SANITIZED_NAME_TO_PERIOD[current_name]
            new_value = clamp_period(value + change)
        else:
            current_name = sanitize_pitch(dpg.get_value(input_tag))
            if current_name not in SANITIZED_NAME_TO_PITCH:
                return

            value = SANITIZED_NAME_TO_PITCH[current_name]
            new_value = clamp_pitch(value + change)

        self._update_initial_pitch_display(
            new_value,
            generator_name,
            input_tag,
            value_tag,
        )

    def _update_initial_pitch_display(
        self,
        value: int,
        generator_name: GeneratorName,
        input_tag: str,
        value_tag: str,
    ) -> None:
        _, display_value = self._format_initial_pitch(generator_name, value)
        dpg_set_value(input_tag, display_value)
        dpg_set_value(value_tag, str(value))
        self._on_initial_pitch_changed(generator_name, value)

    def _validate_and_update_initial_pitch_input(
        self,
        sender: Sender,
        app_data: str,
        user_data: Tuple[GeneratorName, str, str],
    ) -> None:
        generator_name, input_tag, value_tag = user_data
        try:
            value = int(app_data)
            if generator_name == GeneratorName.NOISE:
                value = clamp_period(value)
            else:
                value = clamp_pitch(value)
        except ValueError:
            name = app_data.strip()
            if generator_name == GeneratorName.NOISE:
                name = sanitize_period(name)
                if name not in SANITIZED_NAME_TO_PERIOD:
                    value = int(dpg.get_value(value_tag))
                else:
                    value = SANITIZED_NAME_TO_PERIOD[name]
            else:
                name = sanitize_pitch(name)
                if name not in SANITIZED_NAME_TO_PITCH:
                    value = int(dpg.get_value(value_tag))
                else:
                    value = SANITIZED_NAME_TO_PITCH[name]

        self._update_initial_pitch_display(
            value,
            generator_name,
            input_tag,
            value_tag,
        )

    def _create_feature_display(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
        parent: str,
    ) -> GUIBarGraph:
        config = FEATURE_PLOT_CONFIGS[feature_key]
        plot = self._add_bar_plot(parent, config, data, generator_name, feature_key)
        self._add_raw_data_text(parent, generator_name, feature_key, config, plot, data)
        return plot

    def _calculate_plot_limits(
        self,
        config: FeaturePlotConfig,
        data: np.ndarray,
    ) -> Tuple[int, int, Optional[Tuple[int, ...]]]:
        y_min = config.y_min
        y_max = config.y_max
        y_ticks = config.y_ticks
        if y_min == -1.0 and y_max == -1.0:
            max_abs_value = float(np.max(np.abs(data)))
            y_min = -max_abs_value
            y_max = max_abs_value

            step = max(1, int(np.ceil(max_abs_value / 4)))
            max_tick = step * 4
            y_ticks = tuple(range(-max_tick, max_tick + 1, step))

        y_min, y_max = extend_y_range(y_min, y_max)
        return y_min, y_max, y_ticks

    def _add_bar_plot(
        self,
        parent: str,
        config: FeaturePlotConfig,
        data: np.ndarray,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
    ) -> GUIBarGraph:
        plot_tag = self._get_feature_plot_tag(generator_name, feature_key)
        y_min, y_max, _ = self._calculate_plot_limits(config, data)
        plot = GUIBarGraph(
            tag=plot_tag,
            parent=parent,
            data_range=config.data_range,
            width=DIM_BAR_PLOT_WIDTH,
            height=DIM_BAR_PLOT_HEIGHT,
            label=config.label,
            y_range=(y_min, y_max),
        )

        self._graphs[plot_tag] = plot
        if data.size == 0:
            return plot

        self._configure_plot_data(
            plot,
            generator_name,
            feature_key,
            config,
            data,
        )

        return plot

    def _configure_plot_data(
        self,
        plot: GUIBarGraph,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        config: FeaturePlotConfig,
        data: np.ndarray,
    ) -> None:
        self._load_plot_data(plot, generator_name, feature_key, config, data)
        plot.set_callbacks(
            on_bar_point_clicked=lambda data: self._on_bar_point_clicked(
                generator_name,
                feature_key,
                data,
                plot.plot_tag,
            ),
            on_bar_point_hovered=self._on_bar_point_hovered,
        )

    def _on_initial_pitch_changed(
        self,
        generator_name: GeneratorName,
        initial_pitch: int,
    ) -> None:
        self._schedule_on_reconstruction_instrument_updated(
            generator_name,
            FeatureKey.INITIAL_PITCH,
            initial_pitch,
        )

    def _schedule_on_reconstruction_instrument_updated(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: FeatureValue,
    ) -> None:
        self._pending_reconstruction_update = ReconstructionUpdate(generator_name, feature_key, data)
        CallbackQueue.add(
            self._on_reconstruction_instrument_updated,
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_SCHEDULE,
        )

    def _on_reconstruction_instrument_updated(self) -> None:
        if self._pending_reconstruction_update is not None:
            generator_name, feature_key, data = self._pending_reconstruction_update
            self._pending_reconstruction_update = None
            self.call(
                self.on_reconstruction_instrument_updated,
                generator_name,
                self._get_features(generator_name),
                feature_key,
                data,
            )

    def _get_features(self, generator_name: GeneratorName) -> Features:
        assert self.current_features is not None, "Current features should not be None when creating feature plots"
        feature_data = self.current_features.model_copy()
        features = feature_data.get_generator_features(generator_name)
        assert features is not None, f"Features for generator {generator_name} should not be None"
        return features

    def _format_data(self, data: np.ndarray) -> str:
        string_data = [str(clamp(int(value), -128, 127)) for value in data]
        return " ".join(string_data)

    def _on_bar_point_clicked(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
        plot_tag: str,
    ) -> None:
        raw_data_tag = f"{plot_tag}{SUF_GRAPH_RAW_DATA}"
        dpg_set_value(raw_data_tag, self._format_data(data))
        self._schedule_on_reconstruction_instrument_updated(
            generator_name,
            feature_key,
            data,
        )

    def _on_bar_point_hovered(self, label: Optional[str], index: Optional[int]) -> None:
        self.call(self.on_reconstruction_instrument_hovered, index)
        if label is not None:
            GUIStatusBar.set(MSG_STATUS_RECONSTRUCTIONS_DETAILS_BAR.format(instrument_feature=label))

    def _add_raw_data_text(
        self,
        parent: str,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        config: FeaturePlotConfig,
        plot: GUIBarGraph,
        data: np.ndarray,
    ) -> None:
        text_group_tag = self._get_feature_text_group_tag(generator_name, feature_key)
        raw_data_text = self._format_data(data)
        raw_data_tag = self._get_feature_text_tag(text_group_tag)
        copy_button_tag = f"{text_group_tag}{SUF_BUTTON_COPY}"

        with dpg.group(tag=text_group_tag, parent=parent, horizontal=True):
            GUIButton(
                tag=copy_button_tag,
                label=LBL_BUTTON_RECONSTRUCTIONS_DETAILS_COPY,
                width=DIM_BUTTON_WIDTH_COPY,
                callback=lambda: self._on_copy_button_clicked(raw_data_text, copy_button_tag),
            )

            dpg.add_input_text(
                tag=raw_data_tag,
                default_value=raw_data_text,
                width=-1,
                multiline=False,
                on_enter=True,
                decimal=False,
                callback=self._parse_raw_data_input,
                user_data=(
                    generator_name,
                    feature_key,
                    config,
                    plot,
                ),
            )

        self.shortcut_manager.setup_input_focus_handlers(raw_data_tag)
        GUIStatusBar.bind_to_item(copy_button_tag, MSG_STATUS_RECONSTRUCTIONS_DETAILS_COPY_SEQUENCE)
        GUIStatusBar.bind_to_item(
            raw_data_tag,
            MSG_STATUS_RECONSTRUCTIONS_DETAILS_SEQUENCE.format(
                instrument_feature=feature_key.capitalized,
            ),
        )

    def _parse_raw_data_input(
        self,
        sender: Sender,
        app_data: str,
        user_data: Tuple[GeneratorName, FeatureKey, FeaturePlotConfig, GUIBarGraph],
    ) -> None:
        generator_name, feature_key, config, plot = user_data
        data_range = config.data_range if config.data_range is not None else (-128, 127)
        try:
            raw_data_items = app_data.strip().split()
            raw_data = np.array(
                [clamp(int(value), *data_range) for value in raw_data_items],
                dtype=np.int8,
            )
            self.theme.bind_to_item(sender)
        except ValueError:
            logger.error(f"Invalid {generator_name.name} data input for {feature_key.name}: {app_data}")
            self.invalid_input_theme.bind_to_item(sender)
            return

        dpg.set_value(sender, self._format_data(raw_data))
        self._schedule_on_reconstruction_instrument_updated(
            generator_name,
            feature_key,
            raw_data,
        )

        self._load_plot_data(plot, generator_name, feature_key, config, raw_data)

    def _load_plot_data(
        self,
        plot: GUIBarGraph,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        config: FeaturePlotConfig,
        data: np.ndarray,
    ) -> None:
        _, _, y_ticks = self._calculate_plot_limits(config, data)
        name = f"{generator_name.capitalize()}: {feature_key.capitalized}"
        plot.load_data(
            data=data,
            name=name,
            color=config.color,
            y_ticks=y_ticks,
        )

    def _on_copy_button_clicked(self, text: str, button_tag: str) -> None:
        copy_to_clipboard(text, LBL_BUTTON_RECONSTRUCTIONS_DETAILS_COPY, button_tag)

    @property
    def current_features(self) -> Optional[FeatureData]:
        return self.reconstruction_manager.current_features

    @current_features.setter
    def current_features(self, value: Optional[FeatureData]) -> None:
        self.reconstruction_manager.current_features = value
