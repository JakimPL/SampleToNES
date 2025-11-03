import threading
from typing import Callable, Dict, Optional

import dearpygui.dearpygui as dpg
import numpy as np

from browser.graphs.bar import GUIBarPlotDisplay
from browser.panels.panel import GUIPanel
from browser.reconstruction.config import FEATURE_DISPLAY_ORDER, FEATURE_PLOT_CONFIGS
from browser.reconstruction.feature import FeatureData
from constants.browser import (
    DIM_BAR_PLOT_DEFAULT_HEIGHT,
    DIM_COPY_BUTTON_WIDTH,
    LBL_COPIED_TOOLTIP,
    LBL_COPY_BUTTON,
    LBL_RECONSTRUCTION_DETAILS,
    LBL_RECONSTRUCTION_EXPORT_FTI,
    MSG_RECONSTRUCTION_NO_DATA,
    SUF_GRAPH_COPY_BUTTON,
    SUF_GRAPH_RAW_DATA,
    SUF_GRAPH_RAW_DATA_GROUP,
    SUF_NO_DATA_MESSAGE,
    SUF_SEPARATOR,
    TAG_RECONSTRUCTION_DETAILS_PANEL,
    TAG_RECONSTRUCTION_DETAILS_TAB_BAR,
    TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON,
    TAG_RECONSTRUCTION_PANEL_GROUP,
    VAL_PLOT_WIDTH_FULL,
)
from constants.enums import FeatureKey, GeneratorName
from reconstructor.reconstruction import Reconstruction


class GUIReconstructionDetailsPanel(GUIPanel):
    def __init__(self) -> None:
        self.current_features: Optional[FeatureData] = None
        self.generator_plots: Dict[GeneratorName, Dict[FeatureKey, GUIBarPlotDisplay]] = {}
        self.tab_bar_tag = TAG_RECONSTRUCTION_DETAILS_TAB_BAR
        self.no_data_message_tag = f"{TAG_RECONSTRUCTION_DETAILS_PANEL}{SUF_NO_DATA_MESSAGE}"
        self.export_button_separator_tag = f"{TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON}{SUF_SEPARATOR}"
        self._on_instrument_export = None

        super().__init__(
            tag=TAG_RECONSTRUCTION_DETAILS_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
        )

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, parent=self.parent_tag, autosize_x=True, autosize_y=True):
            dpg.add_text(LBL_RECONSTRUCTION_DETAILS)
            dpg.add_separator()

            dpg.add_button(
                tag=TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON,
                label=LBL_RECONSTRUCTION_EXPORT_FTI,
                width=-1,
                callback=self._handle_export_button_clicked,
                show=False,
            )
            dpg.add_separator(tag=self.export_button_separator_tag, show=False)

            dpg.add_text(
                tag=self.no_data_message_tag,
                default_value=MSG_RECONSTRUCTION_NO_DATA,
                show=True,
            )

    def set_callback(self, on_instrument_export: Optional[Callable[[], None]] = None) -> None:
        self._on_instrument_export = on_instrument_export

    def _handle_export_button_clicked(self) -> None:
        if self._on_instrument_export is not None and self.current_features is not None:
            self._on_instrument_export()

    def _clear_tabs(self) -> None:
        if dpg.does_item_exist(self.tab_bar_tag):
            dpg.delete_item(self.tab_bar_tag)
        self.generator_plots.clear()

    def _create_tabs_for_generators(self, feature_data: FeatureData) -> None:
        self._clear_tabs()

        with dpg.tab_bar(tag=self.tab_bar_tag, parent=self.tag):
            for generator_name in feature_data.get_generator_names():
                self._create_generator_tab(generator_name, feature_data)

    def _create_generator_tab(self, generator_name: GeneratorName, feature_data: FeatureData) -> None:
        tab_tag = f"{self.tab_bar_tag}_{generator_name}"

        with dpg.tab(label=generator_name, parent=self.tab_bar_tag, tag=tab_tag):
            self.generator_plots[generator_name] = {}
            generator_features = feature_data.get_generator_features(generator_name)

            if not generator_features:
                return

            for i, feature_key in enumerate(FEATURE_DISPLAY_ORDER):
                if feature_key in generator_features and feature_key in FEATURE_PLOT_CONFIGS:
                    if i != 0:
                        dpg.add_separator(parent=tab_tag)

                    feature_data_array = generator_features[feature_key]
                    plot = self._create_feature_plot(generator_name, feature_key, feature_data_array)
                    self.generator_plots[generator_name][feature_key] = plot

    def _create_feature_plot(
        self, generator_name: GeneratorName, feature_key: FeatureKey, data: np.ndarray
    ) -> GUIBarPlotDisplay:
        config = FEATURE_PLOT_CONFIGS[feature_key]
        plot_tag = f"{TAG_RECONSTRUCTION_DETAILS_PANEL}_{generator_name}_{feature_key}"
        tab_tag = f"{self.tab_bar_tag}_{generator_name}"

        plot = self._add_bar_plot(plot_tag, tab_tag, config, data)
        self._add_raw_data_text(plot_tag, tab_tag, data)

        return plot

    def _add_bar_plot(self, plot_tag: str, parent_tag: str, config, data: np.ndarray) -> GUIBarPlotDisplay:
        y_min = config.y_min
        y_max = config.y_max

        if y_min == -1.0 and y_max == -1.0:
            max_abs_value = float(np.max(np.abs(data)))
            y_min = -max_abs_value
            y_max = max_abs_value

        y_min -= 1.0
        y_max += 1.0

        plot = GUIBarPlotDisplay(
            tag=plot_tag,
            parent=parent_tag,
            width=VAL_PLOT_WIDTH_FULL,
            height=DIM_BAR_PLOT_DEFAULT_HEIGHT,
            label=config.label,
            y_min=y_min,
            y_max=y_max,
        )

        generator_name = plot_tag.split("_")[-2]
        feature_key = plot_tag.split("_")[-1]
        plot.load_data(
            data=data,
            name=f"{generator_name} - {feature_key}",
            color=config.color,
        )

        return plot

    def _add_raw_data_text(self, plot_tag: str, parent_tag: str, data: np.ndarray) -> None:
        raw_data_text = " ".join(map(str, data.tolist()))
        raw_data_tag = f"{plot_tag}{SUF_GRAPH_RAW_DATA}"
        copy_button_tag = f"{plot_tag}{SUF_GRAPH_COPY_BUTTON}"
        group_tag = f"{plot_tag}{SUF_GRAPH_RAW_DATA_GROUP}"

        with dpg.group(tag=group_tag, parent=parent_tag, horizontal=True):
            dpg.add_button(
                tag=copy_button_tag,
                label=LBL_COPY_BUTTON,
                width=DIM_COPY_BUTTON_WIDTH,
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
        dpg.set_clipboard_text(text)

        if dpg.does_item_exist(button_tag):
            original_label = dpg.get_item_label(button_tag)
            dpg.configure_item(button_tag, label=LBL_COPIED_TOOLTIP)

            def restore_label():
                if dpg.does_item_exist(button_tag):
                    dpg.configure_item(button_tag, label=original_label)

            timer = threading.Timer(1.0, restore_label)
            timer.start()

    def display_reconstruction(self, reconstruction: Reconstruction) -> None:
        feature_data = FeatureData.load(reconstruction)
        self.current_features = feature_data

        if dpg.does_item_exist(self.no_data_message_tag):
            dpg.configure_item(self.no_data_message_tag, show=False)

        if dpg.does_item_exist(TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON):
            dpg.configure_item(TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON, show=True)
            dpg.configure_item(self.export_button_separator_tag, show=True)

        self._create_tabs_for_generators(feature_data)

    def clear_display(self) -> None:
        self.current_features = None
        self._clear_tabs()

        if dpg.does_item_exist(self.no_data_message_tag):
            dpg.configure_item(self.no_data_message_tag, show=True)

        if dpg.does_item_exist(TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON):
            dpg.configure_item(TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON, show=False)
            dpg.configure_item(self.export_button_separator_tag, show=False)
