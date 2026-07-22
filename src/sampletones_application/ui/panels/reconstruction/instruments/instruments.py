from functools import partial
from typing import Any, Callable, Dict, Optional, Tuple, cast

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones_application.categories.elements.global_ import (
    ContextElements,
    DialogElements,
    GlobalMessageElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionsInstrumentsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.pitch import build_pitch_tooltip
from sampletones_application.constants.global_ import TAG_SEPARATOR
from sampletones_application.layout.general.colors import FeatureColors
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.general import (
    SUF_BUTTON_COPY,
    SUF_GROUP,
    SUF_HANDLER_REGISTRY,
    SUF_TEXT,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_INPUT_INVALID,
    TAG_GLOBAL_THEME_INSTRUMENT_TABS,
    TAG_GLOBAL_THEME_PANEL_INSTRUMENT,
)
from sampletones_application.tags.graphs import (
    SUF_GRAPH,
    SUF_GRAPH_RAW_DATA,
)
from sampletones_application.tags.reconstructions import (
    SUF_RECONSTRUCTIONS_INSTRUMENTS_NO_DATA_MESSAGE,
    SUF_RECONSTRUCTIONS_INSTRUMENTS_WINDOW,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_BUTTON_EXPORT_INSTRUMENT,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs.bar import GUIBarGraph
from sampletones_application.ui.elements.graphs.utils import extend_y_range
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.elements.layout.collapse import CollapseAxis
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.pitch_stepper import GUIPitchStepper, PitchStepperStyle
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.reconstruction.instruments.config import (
    FeaturePlotConfig,
    make_feature_plot_configs,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.clipboard import copy_to_clipboard
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_set_value,
)
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_core.constants.enums import (
    FeatureKey,
    GeneratorName,
    LibraryGeneratorName,
)
from sampletones_core.constants.general import MAX_PERIOD, MIN_PITCH
from sampletones_core.exporters import Features
from sampletones_core.features import GENERATOR_KIND, supported_features
from sampletones_core.utils.pitch_kind import (
    PERIOD_VALUE_KIND,
    PITCH_VALUE_KIND,
    PitchValueKind,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.arrays import clamp

OnInstrumentExportCallback = Callable[[GeneratorName], None]
OnReconstructionInstrumentHoveredCallback = Callable[[Optional[int]], None]


class GUIReconstructionInstrumentsPanel(GUIPanel):
    def __init__(
        self,
        *,
        pitch_stepper_style: PitchStepperStyle,
        copy_width: int,
        feature_colors: FeatureColors,
        layout_graphs: GraphsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._status_bar = status_bar

        self.generator_plots: Dict[GeneratorName, Dict[FeatureKey, GUIBarGraph]] = {}
        self._pitch_steppers: Dict[GeneratorName, GUIPitchStepper] = {}

        self.tab_bar_tag = TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR
        self.no_data_message_tag = f"{self.tab_bar_tag}{SUF_RECONSTRUCTIONS_INSTRUMENTS_NO_DATA_MESSAGE}"
        self.mouse_item_handler_tag = f"{TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL}{SUF_HANDLER_REGISTRY}"

        self._graphs: Dict[str, GUIBarGraph] = {}
        self._pitch_stepper_style = pitch_stepper_style
        self._copy_width = copy_width
        self._layout_graphs = layout_graphs
        self._feature_plot_configs = make_feature_plot_configs(
            feature_colors,
            language_manager,
        )

        self.theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)
        self.invalid_input_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_INPUT_INVALID)

        self.on_instrument_export: Optional[OnInstrumentExportCallback] = None
        self.on_reconstruction_instrument_hovered: Optional[OnReconstructionInstrumentHoveredCallback] = None

        self.on_pitch_value_changed: Optional[Callable[[GeneratorName, int], None]] = None
        self.on_bar_data_changed: Optional[Callable[[GeneratorName, FeatureKey, np.ndarray], None]] = None
        self.on_raw_data_changed: Optional[Callable[[GeneratorName, FeatureKey, np.ndarray], None]] = None

        self._lbl_section = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            ReconstructionsInstrumentsElements.SECTION,
        ]
        self._lbl_export_instrument = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            ReconstructionsInstrumentsElements.EXPORT_INSTRUMENT_BUTTON,
        ]
        self._lbl_copy = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            ReconstructionsInstrumentsElements.COPY_BUTTON,
        ]
        self._lbl_initial_period = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            ReconstructionsInstrumentsElements.INITIAL_PERIOD,
        ]
        self._lbl_initial_pitch = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            ReconstructionsInstrumentsElements.INITIAL_PITCH,
        ]
        self._msg_input_pitch = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.MESSAGE,
            ReconstructionsInstrumentsElements.STATUS_INPUT_PITCH,
        ]
        self._msg_input_period = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.MESSAGE,
            ReconstructionsInstrumentsElements.STATUS_INPUT_PERIOD,
        ]
        self._msg_bar = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.MESSAGE,
            ReconstructionsInstrumentsElements.STATUS_BAR,
        ]
        self._msg_sequence = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.MESSAGE,
            ReconstructionsInstrumentsElements.STATUS_SEQUENCE,
        ]
        self._msg_copy_sequence = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.MESSAGE,
            ReconstructionsInstrumentsElements.STATUS_COPY_SEQUENCE,
        ]
        self._msg_export_instrument = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.MESSAGE,
            ReconstructionsInstrumentsElements.STATUS_EXPORT_INSTRUMENT,
        ]
        tooltip_template = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.TEMPLATE,
            ReconstructionsInstrumentsElements.INITIAL_PITCH_TOOLTIP_TEMPLATE,
        ]
        self._pitch_tooltip = build_pitch_tooltip(language_manager, PITCH_VALUE_KIND, tooltip_template)
        self._period_tooltip = build_pitch_tooltip(language_manager, PERIOD_VALUE_KIND, tooltip_template)
        self._msg_reconstruction_no_data = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.RECONSTRUCTION_NO_DATA,
        ]
        self._lbl_copied = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.COPIED,
        ]
        self._generator_labels: Dict[GeneratorName, str] = {
            GeneratorName.PULSE1: language_manager[
                Page.GLOBAL,
                Panel.CONTEXT,
                TextType.LABEL,
                ContextElements.PULSE_1,
            ],
            GeneratorName.PULSE2: language_manager[
                Page.GLOBAL,
                Panel.CONTEXT,
                TextType.LABEL,
                ContextElements.PULSE_2,
            ],
            GeneratorName.TRIANGLE: language_manager[
                Page.GLOBAL,
                Panel.CONTEXT,
                TextType.LABEL,
                ContextElements.TRIANGLE,
            ],
            GeneratorName.NOISE: language_manager[
                Page.GLOBAL,
                Panel.CONTEXT,
                TextType.LABEL,
                ContextElements.NOISE,
            ],
        }

        super().__init__(
            tag=TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
        )

        self._enable_horizontal_collapse(
            initial_collapsed=initial_collapsed,
            side=CollapseAxis.HORIZONTAL_RIGHT,
        )

    def create_panel(self, parent: str) -> None:
        with card(
            parent,
            self.tag,
            auto_resize_y=False,
            height=-1,
            no_scrollbar=True,
        ):
            with self._collapsible_section(
                self._lbl_section,
                glyph=self._glyphs.headers.instruments,
            ):
                self._create_content()

        self._setup_mouse_event_handler()

    def _create_content(self) -> None:
        dpg.add_text(
            tag=self.no_data_message_tag,
            parent=self._body_container,
            default_value=self._msg_reconstruction_no_data,
            show=True,
        )

        with dpg.tab_bar(
            tag=self.tab_bar_tag,
            parent=self._body_container,
            show=False,
        ):
            self._create_tabs_for_generators()

    def _get_generator_tab_tag(self, generator_name: GeneratorName) -> str:
        return f"{self.tab_bar_tag}{TAG_SEPARATOR}{generator_name}"

    def _get_window_tag(self, tab_tag: str) -> str:
        return f"{tab_tag}{SUF_RECONSTRUCTIONS_INSTRUMENTS_WINDOW}"

    def _get_feature_group_tag(self, generator_name: GeneratorName, feature_key: FeatureKey) -> str:
        return f"{self.tab_bar_tag}{TAG_SEPARATOR}{generator_name}{TAG_SEPARATOR}{feature_key}{SUF_GROUP}"

    def _get_feature_text_group_tag(self, generator_name: GeneratorName, feature_key: FeatureKey) -> str:
        return f"{self.tab_bar_tag}{TAG_SEPARATOR}{generator_name}{TAG_SEPARATOR}{feature_key}{SUF_GRAPH_RAW_DATA}"

    def _get_feature_text_tag(self, text_group_tag: str) -> str:
        return f"{text_group_tag}{SUF_TEXT}"

    def _get_feature_plot_tag(self, generator_name: GeneratorName, feature_key: FeatureKey) -> str:
        return f"{self.tab_bar_tag}{TAG_SEPARATOR}{generator_name}{TAG_SEPARATOR}{feature_key}{SUF_GRAPH}"

    def _setup_mouse_event_handler(self) -> None:
        with dpg.handler_registry(tag=self.mouse_item_handler_tag):
            dpg.add_mouse_move_handler(callback=self._on_mouse_move)

    def _handle_export_button_clicked(self, sender: Sender, app_data: Any, user_data: GeneratorName) -> None:
        self.call(self.on_instrument_export, user_data)

    def _create_tabs_for_generators(self) -> None:
        for generator_name in GeneratorName.items():
            self._create_generator_tab(generator_name)

    def _generator_kind(self, generator_name: GeneratorName) -> LibraryGeneratorName:
        return GENERATOR_KIND[generator_name]

    def _generator_features(self, generator_name: GeneratorName) -> list[FeatureKey]:
        return supported_features(self._generator_kind(generator_name))

    def _feature_plot_config(self, generator_name: GeneratorName, feature_key: FeatureKey) -> FeaturePlotConfig:
        return self._feature_plot_configs[self._generator_kind(generator_name)][feature_key]

    def _create_generator_tab(self, generator_name: GeneratorName) -> None:
        tab_tag = self._get_generator_tab_tag(generator_name)
        window_tag = self._get_window_tag(tab_tag)

        with dpg.tab(
            label=self._generator_labels[generator_name],
            tag=tab_tag,
            parent=self.tab_bar_tag,
            show=False,
        ):
            self.generator_plots[generator_name] = {}
            button_tag = f"{TAG_RECONSTRUCTIONS_INSTRUMENTS_BUTTON_EXPORT_INSTRUMENT}{TAG_SEPARATOR}{tab_tag}"
            GUIButton(
                tag=button_tag,
                parent=tab_tag,
                label=self._lbl_export_instrument,
                width=-1,
                callback=self._handle_export_button_clicked,
                user_data=generator_name,
            )
            self._status_bar.bind_to_item(
                button_tag,
                self._msg_export_instrument.format(generator=self._generator_labels[generator_name]),
            )

            with dpg.child_window(
                tag=window_tag,
                parent=tab_tag,
                height=-1,
            ):
                self._create_generator_content(generator_name, window_tag)

            ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_INSTRUMENT).bind_to_item(window_tag)

        ThemeRegistry.get(TAG_GLOBAL_THEME_INSTRUMENT_TABS).bind_to_item(tab_tag)

    def _create_generator_content(self, generator_name: GeneratorName, window_tag: str) -> None:
        initial_pitch = self._default_initial_pitch(generator_name)
        self._create_pitch_stepper(generator_name, initial_pitch, window_tag)
        self._create_generator_feature_displays(generator_name, window_tag)

    def _default_initial_pitch(self, generator_name: GeneratorName) -> int:
        return MAX_PERIOD if generator_name == GeneratorName.NOISE else MIN_PITCH

    def _create_generator_feature_displays(self, generator_name: GeneratorName, window_tag: str) -> None:
        for feature_key in self._generator_features(generator_name):
            self._add_generator_feature_display(generator_name, feature_key, window_tag)

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

    def _apply_pitch_display(
        self,
        generator_name: GeneratorName,
        value: int,
    ) -> None:
        stepper = self._pitch_steppers.get(generator_name)
        if stepper is not None:
            stepper.set_value(value)

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

        config = self._feature_plot_config(generator_name, feature_key)
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

    def update_view(
        self,
        view_model: ReconstructionInstrumentsViewModel,
    ) -> None:
        is_loaded = view_model.reconstruction_loaded
        dpg_configure_item(self.no_data_message_tag, show=not is_loaded)
        dpg_configure_item(self.tab_bar_tag, show=is_loaded)

        for generator_name in GeneratorName.items():
            tab_tag = self._get_generator_tab_tag(generator_name)
            is_available = generator_name in view_model.available_generators
            dpg_configure_item(tab_tag, show=is_available)

    def update_feature_data(
        self,
        generators: Optional[Dict[GeneratorName, Features]],
    ) -> None:
        if generators is None:
            return

        for generator_name in GeneratorName.items():
            generator_features = generators.get(generator_name)
            if generator_features is None:
                continue

            self._update_generator_feature_data(generator_name, generator_features)

    def _update_generator_feature_data(
        self,
        generator_name: GeneratorName,
        generator_features: Features,
    ) -> None:
        initial_pitch = cast(int, generator_features[FeatureKey.INITIAL_PITCH])
        self._apply_pitch_display(generator_name, initial_pitch)

        for feature_key in self._generator_features(generator_name):
            self._update_generator_feature_display(
                generator_name,
                generator_features,
                feature_key,
            )

    def _update_generator_feature_display(
        self,
        generator_name: GeneratorName,
        generator_features: Features,
        feature_key: FeatureKey,
    ) -> None:
        feature = self._feature_array(generator_features, feature_key)
        self._update_generator_plot(generator_name, feature_key, feature)
        self._update_raw_data_text(generator_name, feature_key, feature)

    def _feature_array(
        self,
        generator_features: Features,
        feature_key: FeatureKey,
    ) -> np.ndarray:
        feature = cast(Optional[np.ndarray], generator_features.get(feature_key))
        if feature is None:
            return np.array([], dtype=np.int8)
        return feature

    def _pitch_kind(self, generator_name: GeneratorName) -> PitchValueKind:
        return PERIOD_VALUE_KIND if generator_name == GeneratorName.NOISE else PITCH_VALUE_KIND

    def _create_pitch_stepper(
        self,
        generator_name: GeneratorName,
        initial_pitch: int,
        parent: str,
    ) -> None:
        is_noise = generator_name == GeneratorName.NOISE
        kind = self._pitch_kind(generator_name)
        stepper = GUIPitchStepper(
            tag=parent,
            parent=parent,
            kind=kind,
            initial_value=initial_pitch,
            label=self._lbl_initial_period if is_noise else self._lbl_initial_pitch,
            tooltip=self._period_tooltip if is_noise else self._pitch_tooltip,
            status_message=self._msg_input_period if is_noise else self._msg_input_pitch,
            status_bar=self._status_bar,
            layout=self._pitch_stepper_style.dimensions,
            plus_minus_layout=self._pitch_stepper_style.plus_minus,
            value_color=self._pitch_stepper_style.value_color,
        )
        stepper.on_value_changed = partial(
            self._on_pitch_value_changed,
            generator_name,
        )
        self._pitch_steppers[generator_name] = stepper

    def _on_pitch_value_changed(
        self,
        generator_name: GeneratorName,
        value: int,
    ) -> None:
        self.call(self.on_pitch_value_changed, generator_name, value)

    def _on_mouse_move(self, sender: Sender, app_data: Tuple[int, int]) -> None:
        tab = dpg.get_value(self.tab_bar_tag)
        if not tab:
            self.call(self.on_reconstruction_instrument_hovered, None)
            return

        tab_tag = dpg.get_item_alias(tab)
        window_tag = self._get_window_tag(tab_tag)
        if not tab_tag or (not dpg.is_item_hovered(tab_tag) and not dpg.is_item_hovered(window_tag)):
            self.call(self.on_reconstruction_instrument_hovered, None)

    def _create_feature_display(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
        parent: str,
    ) -> GUIBarGraph:
        config = self._feature_plot_config(generator_name, feature_key)
        plot = self._add_bar_plot(
            parent,
            config,
            data,
            generator_name,
            feature_key,
        )
        self._add_raw_data_text(
            parent,
            generator_name,
            feature_key,
            config,
            plot,
            data,
        )
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
            layout=self._layout_graphs,
            language_manager=None,
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

    def _on_bar_point_clicked(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
        plot_tag: str,
    ) -> None:
        raw_data_tag = f"{plot_tag}{SUF_GRAPH_RAW_DATA}"
        dpg_set_value(raw_data_tag, self._format_data(data))
        self.call(self.on_bar_data_changed, generator_name, feature_key, data)

    def _on_bar_point_hovered(
        self,
        label: Optional[str],
        index: Optional[int],
    ) -> None:
        self.call(self.on_reconstruction_instrument_hovered, index)
        if label is not None:
            self._status_bar.set(self._msg_bar.format(instrument_feature=label))

    def _add_raw_data_text(
        self,
        parent: str,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        config: FeaturePlotConfig,
        plot: GUIBarGraph,
        data: np.ndarray,
    ) -> None:
        text_group_tag = self._get_feature_text_group_tag(
            generator_name,
            feature_key,
        )
        raw_data_text = self._format_data(data)
        raw_data_tag = self._get_feature_text_tag(text_group_tag)
        copy_button_tag = f"{text_group_tag}{SUF_BUTTON_COPY}"

        with dpg.group(tag=text_group_tag, parent=parent, horizontal=True):
            GUIButton(
                tag=copy_button_tag,
                label=self._lbl_copy,
                width=self._copy_width,
                callback=lambda: self._on_copy_button_clicked(
                    raw_data_text,
                    copy_button_tag,
                ),
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
            FontRegistry.bind_to_item(raw_data_tag, Font.MONO)

        self._status_bar.bind_to_item(copy_button_tag, self._msg_copy_sequence)
        self._status_bar.bind_to_item(
            raw_data_tag,
            self._msg_sequence.format(
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
        self.call(self.on_raw_data_changed, generator_name, feature_key, raw_data)
        self._load_plot_data(plot, generator_name, feature_key, config, raw_data)

    def _format_data(self, data: np.ndarray) -> str:
        string_data = [str(clamp(int(value), -128, 127)) for value in data]
        return " ".join(string_data)

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
        copy_to_clipboard(
            text,
            self._lbl_copy,
            button_tag,
            copied_label=self._lbl_copied,
        )
