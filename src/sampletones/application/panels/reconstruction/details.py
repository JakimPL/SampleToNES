from typing import Any, Callable, Dict, Optional, Tuple, cast

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.constants.enums import FeatureKey, GeneratorName
from sampletones.exporters import Features
from sampletones.reconstructions import Reconstruction
from sampletones.typehints import Sender, VoidCallback
from sampletones.utils import (
    NAME_TO_PERIOD,
    NAME_TO_PITCH,
    clamp_period,
    clamp_pitch,
    hash_model,
    period_to_name,
    pitch_to_name,
)

from ...constants.general import (
    COL_TEXT_DISABLED_DEFAULT,
    DIM_BUTTON_INPUT_INT,
    DIM_BUTTON_WIDTH_COPY,
    MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
    SUF_BUTTON_COPY,
    SUF_DECREMENT,
    SUF_INCREMENT,
    SUF_INPUT,
    SUF_LABEL,
    SUF_PANEL_RIGHT,
    SUF_TABLE,
    SUF_TEXT,
    TAG_TAB_RECONSTRUCTIONS,
    VAL_CHARACTER_BUTTON_DECREMENT,
    VAL_CHARACTER_BUTTON_INCREMENT,
)
from ...constants.graphs import (
    DIM_BAR_PLOT_HEIGHT,
    DIM_BAR_PLOT_WIDTH,
    SUF_GRAPH_RAW_DATA,
    SUF_GRAPH_RAW_DATA_GROUP,
)
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
    SUF_RECONSTRUCTIONS_DETAILS_WINDOW,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_NO_DATA_MESSAGE,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_SEPARATOR,
    TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI,
    TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
    TAG_PANEL_RECONSTRUCTIONS_DETAILS,
    TAG_TAB_BAR_RECONSTRUCTIONS_DETAILS,
    TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
    TPL_TOOLTIP_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.graphs.bar import GUIBarGraph
from ...elements.panel import GUIPanel
from ...reconstruction.config import (
    FEATURE_DISPLAY_ORDER,
    FEATURE_PLOT_CONFIGS,
    FeaturePlotConfig,
)
from ...reconstruction.feature import FeatureData
from ...themes.table import InitialPitchTableTheme
from ...utils.clipboard import copy_to_clipboard
from ...utils.dpg import dpg_configure_item, dpg_delete_item, dpg_set_value
from ...utils.thread import concurrent
from ...utils.tooltip import show_tooltip

OnInstrumentExportCallback = Callable[[GeneratorName], None]
OnReconstructionInstrumentUpdatedCallback = Callable[[GeneratorName, Features, FeatureKey, np.ndarray], None]


class GUIReconstructionDetailsPanel(GUIPanel):
    def __init__(self) -> None:
        self.reconstruction_hash: str = ""
        self.current_features: Optional[FeatureData] = None
        self.generator_plots: Dict[GeneratorName, Dict[FeatureKey, GUIBarGraph]] = {}

        self.tab_bar_tag = TAG_TAB_BAR_RECONSTRUCTIONS_DETAILS
        self.no_data_message_tag = f"{self.tab_bar_tag}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_NO_DATA_MESSAGE}"
        self.export_button_separator_tag = f"{self.tab_bar_tag}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_SEPARATOR}"

        self.initial_pitch_theme = InitialPitchTableTheme()

        self._on_instrument_export: Optional[OnInstrumentExportCallback] = None
        self._on_instruments_export: Optional[VoidCallback] = None
        self._on_reconstruction_instrument_updated: Optional[OnReconstructionInstrumentUpdatedCallback] = None

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
        dpg.add_separator(tag=self.export_button_separator_tag, show=False)
        dpg.add_text(
            tag=self.no_data_message_tag,
            default_value=MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
            show=True,
        )

    def set_callbacks(
        self,
        on_instrument_export: Optional[OnInstrumentExportCallback] = None,
        on_instruments_export: Optional[VoidCallback] = None,
        on_reconstruction_instrument_updated: Optional[OnReconstructionInstrumentUpdatedCallback] = None,
    ) -> None:
        if on_instrument_export is not None:
            self._on_instrument_export = on_instrument_export
        if on_instruments_export is not None:
            self._on_instruments_export = on_instruments_export
        if on_reconstruction_instrument_updated is not None:
            self._on_reconstruction_instrument_updated = on_reconstruction_instrument_updated

    def _export_instruments(self) -> None:
        if self._on_instruments_export is not None:
            self._on_instruments_export()

    def _handle_export_button_clicked(self, sender: Sender, app_data: Any, user_data: GeneratorName) -> None:
        if self._on_instrument_export is not None:
            self._on_instrument_export(user_data)

    def _clear_tabs(self) -> None:
        dpg_delete_item(self.export_button_separator_tag)
        dpg_delete_item(self.tab_bar_tag)
        dpg_delete_item(TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS)
        self._clear_generator_plots()

    def _clear_generator_plots(self) -> None:
        for plots in self.generator_plots.values():
            for plot in plots.values():
                dpg_delete_item(plot.tag)
                dpg_delete_item(plot.mouse_handler_tag)

        self.generator_plots.clear()

    def _create_tabs_for_generators(self, feature_data: FeatureData) -> None:
        self._clear_tabs()

        dpg.add_separator(tag=self.export_button_separator_tag, parent=self.tag)
        dpg.add_text(
            LBL_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
            tag=TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
            parent=self.tag,
        )
        with dpg.tab_bar(tag=self.tab_bar_tag, parent=self.tag):
            for generator_name in feature_data.get_generator_names():
                self._create_generator_tab(generator_name, feature_data)

    def _create_generator_tab(self, generator_name: GeneratorName, feature_data: FeatureData) -> None:
        tab_tag = f"{self.tab_bar_tag}_{generator_name}"
        window_tag = f"{tab_tag}{SUF_RECONSTRUCTIONS_DETAILS_WINDOW}"

        dpg_delete_item(tab_tag)
        dpg_delete_item(window_tag)
        with dpg.tab(label=generator_name, parent=self.tab_bar_tag, tag=tab_tag):
            self.generator_plots[generator_name] = {}
            generator_features = feature_data.get_generator_features(generator_name)

            if not generator_features:
                return

            button_tag = f"{TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI}_{tab_tag}"
            GUIButton(
                tag=button_tag,
                label=LBL_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI,
                width=-1,
                parent=window_tag,
                callback=self._handle_export_button_clicked,
                user_data=generator_name,
            )

            with dpg.child_window(tag=window_tag, parent=tab_tag):
                initial_pitch = cast(int, generator_features.get(FeatureKey.INITIAL_PITCH))
                self._add_initial_pitch_display(generator_name, initial_pitch, window_tag)

                feature_keys = [
                    key
                    for key in FEATURE_DISPLAY_ORDER
                    if key in generator_features.keys() and key in FEATURE_PLOT_CONFIGS
                ]

                for feature_key in feature_keys:
                    dpg.add_separator(parent=window_tag)
                    feature_data_array = cast(np.ndarray, generator_features[feature_key])
                    plot = self._create_feature_plot(generator_name, feature_key, feature_data_array, window_tag)
                    if plot:
                        self.generator_plots[generator_name][feature_key] = plot

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
            )
            dpg.add_table_column(
                width=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_DISPLAY,
                width_fixed=True,
            )
            dpg.add_table_column(width_stretch=True)
            dpg.add_table_column(
                width=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_BUTTON,
                width_fixed=True,
            )
            dpg.add_table_column(
                width=DIM_TABLE_CELL_WIDTH_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH_BUTTON,
                width_fixed=True,
            )
            with dpg.table_row():
                dpg.add_text(label, tag=input_label_tag)
                dpg.add_text(
                    str(initial_pitch),
                    tag=value_tag,
                    color=COL_TEXT_DISABLED_DEFAULT,
                )
                dpg.add_input_text(
                    tag=input_tag,
                    default_value=display_value,
                    width=-1,
                    callback=self._validate_and_update_initial_pitch_input,
                    on_enter=True,
                    user_data=(
                        generator_name,
                        input_tag,
                        value_tag,
                    ),
                )
                dpg.add_button(
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
                dpg.add_button(
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

        with dpg.handler_registry():
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

    def _on_mouse_down(
        self,
        sender: Sender,
        app_data: Any,
        user_data: Tuple[str, str, GeneratorName, str, str],
    ) -> None:
        decrement_button_tag, increment_button_tag, generator_name, input_tag, value_tag = user_data

        if dpg.is_item_hovered(decrement_button_tag):
            pitch_change_data = (generator_name, input_tag, value_tag, -1)
            self._change_initial_pitch(sender, app_data, pitch_change_data)
        elif dpg.is_item_hovered(increment_button_tag):
            pitch_change_data = (generator_name, input_tag, value_tag, 1)
            self._change_initial_pitch(sender, app_data, pitch_change_data)

    def _create_initial_pitch_tooltip(self, generator_name: GeneratorName, input_tag: str) -> None:
        if generator_name == GeneratorName.NOISE:
            pitch_type = "period"
            example_name = "p508"
            example_value = NAME_TO_PERIOD[example_name]
        else:
            pitch_type = "pitch"
            example_name = "C-4"
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
        generator_name, input_tag, value_tag, change = user_data
        current_name = dpg.get_value(input_tag).strip()
        if generator_name == GeneratorName.NOISE:
            if current_name not in NAME_TO_PERIOD:
                return

            value = NAME_TO_PERIOD[current_name]
            new_value = clamp_period(value + change)
        else:
            if current_name not in NAME_TO_PITCH:
                return

            value = NAME_TO_PITCH[current_name]
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
        dpg_set_value(value_tag, value)

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
                if name not in NAME_TO_PERIOD:
                    value = int(dpg.get_value(value_tag))
                else:
                    value = NAME_TO_PERIOD[name]
            else:
                if name not in NAME_TO_PITCH:
                    value = int(dpg.get_value(value_tag))
                else:
                    value = NAME_TO_PITCH[name]

        self._update_initial_pitch_display(
            value,
            generator_name,
            input_tag,
            value_tag,
        )

    def _create_feature_plot(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
        parent: str,
    ) -> Optional[GUIBarGraph]:
        config = FEATURE_PLOT_CONFIGS[feature_key]
        plot_tag = f"{self.tag}_{self.reconstruction_hash}_{generator_name}_{feature_key}"
        if data.size == 0:
            return None

        plot = self._add_bar_plot(plot_tag, parent, config, data, generator_name, feature_key)
        self._add_raw_data_text(plot_tag, parent, data)

        return plot

    def _add_bar_plot(
        self,
        plot_tag: str,
        parent: str,
        config: FeaturePlotConfig,
        data: np.ndarray,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
    ) -> GUIBarGraph:
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

        gap = max(1.0, y_min * 0.1, y_max * 0.1)
        y_min = int(np.floor(y_min - gap))
        y_max = int(np.ceil(y_max + gap))

        plot = GUIBarGraph(
            tag=plot_tag,
            parent=parent,
            data_range=config.data_range,
            width=DIM_BAR_PLOT_WIDTH,
            height=DIM_BAR_PLOT_HEIGHT,
            label=config.label,
            y_min=y_min,
            y_max=y_max,
        )

        plot.load_data(
            data=data,
            name=f"{generator_name} - {feature_key}",
            color=config.color,
            y_ticks=y_ticks,
        )

        assert self.current_features is not None, "Current features should not be None when creating feature plots"
        feature_data = self.current_features.model_copy()
        features = feature_data.get_generator_features(generator_name)
        assert features is not None, f"Features for generator {generator_name} should not be None"

        plot.set_callbacks(
            on_bar_point_clicked=lambda data: self._on_bar_point_clicked(
                generator_name,
                features,
                feature_key,
                data,
            )
        )

        return plot

    def _on_bar_point_clicked(
        self,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        if self._on_reconstruction_instrument_updated is not None:
            self._on_reconstruction_instrument_updated(
                generator_name,
                features,
                feature_key,
                data,
            )

    def _add_raw_data_text(self, plot_tag: str, parent: str, data: np.ndarray) -> None:
        raw_data_text = " ".join(map(str, data.tolist()))
        raw_data_tag = f"{plot_tag}{SUF_GRAPH_RAW_DATA}"
        copy_button_tag = f"{plot_tag}{SUF_BUTTON_COPY}"
        group_tag = f"{plot_tag}{SUF_GRAPH_RAW_DATA_GROUP}"

        with dpg.group(tag=group_tag, parent=parent, horizontal=True):
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
                readonly=True,
                multiline=False,
            )

    def _on_copy_button_clicked(self, text: str, button_tag: str) -> None:
        copy_to_clipboard(text, LBL_BUTTON_RECONSTRUCTIONS_DETAILS_COPY, button_tag)

    @concurrent(wait=True, method_bound=True)
    def display_reconstruction(self, reconstruction: Reconstruction) -> None:
        feature_data = FeatureData.load(reconstruction)
        self.current_features = feature_data
        self.reconstruction_hash = hash_model(reconstruction)

        dpg_configure_item(self.no_data_message_tag, show=False)
        dpg_configure_item(TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS, show=True, enabled=True)
        self._create_tabs_for_generators(feature_data)

    def clear_display(self) -> None:
        self.current_features = None
        dpg_configure_item(TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS, show=False, enabled=False)

        self._clear_tabs()
        dpg_configure_item(self.no_data_message_tag, show=True)
        dpg_configure_item(TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI, show=False)
        dpg_configure_item(self.export_button_separator_tag, show=False)
