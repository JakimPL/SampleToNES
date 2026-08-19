from functools import partial
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones_application.categories.context import channel_label, context_label, context_text
from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.hierarchy import TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.pitch import PitchTooltips
from sampletones_application.layout.general.colors.feature import FeatureColors
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_COPY,
    SUF_GROUP,
    SUF_HANDLER_REGISTRY,
    SUF_TEXT,
    SUF_TOOLTIP,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_INPUT_INVALID,
    TAG_GLOBAL_THEME_INPUT_WARNING,
    TAG_GLOBAL_THEME_INSTRUMENT_TABS,
    TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED,
    TAG_GLOBAL_THEME_PANEL_INSTRUMENT,
)
from sampletones_application.tags.graphs import (
    SUF_GRAPH,
    SUF_GRAPH_RAW_DATA,
)
from sampletones_application.tags.reconstructions import (
    SUF_RECONSTRUCTIONS_INSTRUMENTS_INSTRUMENT_SIZE,
    SUF_RECONSTRUCTIONS_INSTRUMENTS_NO_DATA_MESSAGE,
    SUF_RECONSTRUCTIONS_INSTRUMENTS_WINDOW,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_BUTTON_EXPORT_INSTRUMENT,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_TEXT_SAMPLE_SIZE,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs.bar import GUIBarGraph
from sampletones_application.ui.elements.graphs.utils import extend_y_range
from sampletones_application.ui.elements.layout.card import card
from sampletones_application.ui.elements.layout.collapse import CollapseAxis
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.pitch_stepper import (
    GUIPitchStepper,
    PitchStepperStyle,
)
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
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import (
    ChannelName,
    FeatureKey,
    LibraryGeneratorName,
)
from sampletones_core.exporters import Features
from sampletones_core.features import CHANNEL_GENERATOR_KIND, resting_reference, supported_features
from sampletones_core.formats.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
)
from sampletones_core.utils.pitch_kind import (
    PERIOD_VALUE_KIND,
    PITCH_VALUE_KIND,
    PitchValueKind,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.arrays import clamp

OnInstrumentExportCallback = Callable[[ChannelName], None]
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
        self._language_manager = language_manager
        self._status_bar = status_bar

        self.channel_plots: Dict[ChannelName, Dict[FeatureKey, GUIBarGraph]] = {}
        self._pitch_steppers: Dict[ChannelName, GUIPitchStepper] = {}
        self._export_buttons: Dict[ChannelName, GUIButton] = {}

        self.tab_bar_tag = TAG_RECONSTRUCTIONS_INSTRUMENTS_TABS_BAR
        self.no_data_message_tag = compose_tag(self.tab_bar_tag, SUF_RECONSTRUCTIONS_INSTRUMENTS_NO_DATA_MESSAGE)
        self.mouse_item_handler_tag = compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL, SUF_HANDLER_REGISTRY)
        self.sample_size_tag = TAG_RECONSTRUCTIONS_INSTRUMENTS_TEXT_SAMPLE_SIZE
        self.sample_size_group_tag = compose_tag(self.sample_size_tag, SUF_GROUP)

        self._graphs: Dict[str, GUIBarGraph] = {}
        self._sequence_lengths: Dict[Tuple[ChannelName, FeatureKey], int] = {}
        self._pitch_stepper_style = pitch_stepper_style
        self._copy_width = copy_width
        self._layout_graphs = layout_graphs
        self._feature_plot_configs = make_feature_plot_configs(
            feature_colors,
            language_manager,
        )

        self.theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)
        self.invalid_input_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_INPUT_INVALID)
        self.warning_input_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_INPUT_WARNING)

        self.on_instrument_export: Optional[OnInstrumentExportCallback] = None
        self.on_reconstruction_instrument_hovered: Optional[OnReconstructionInstrumentHoveredCallback] = None

        self.on_pitch_value_changed: Optional[Callable[[ChannelName, int], None]] = None
        self.on_bar_data_changed: Optional[Callable[[ChannelName, FeatureKey, np.ndarray], None]] = None
        self.on_raw_data_changed: Optional[Callable[[ChannelName, FeatureKey, np.ndarray], None]] = None

        self._lbl_copy = language_manager["reconstructions.instruments.label.copy_button"]
        self._lbl_sample_size = context_label(language_manager, ContextElements.SAMPLE_SIZE)
        self._lbl_instrument_size = context_label(language_manager, ContextElements.INSTRUMENT_SIZE)
        self._tpl_size_bytes = context_text(language_manager, TextType.TEMPLATE, ContextElements.SIZE_BYTES)
        self._tip_size_bytes = context_text(language_manager, TextType.TOOLTIP, ContextElements.SIZE_BYTES)
        self._pitch_tooltips = PitchTooltips.build(
            language_manager,
            language_manager["reconstructions.instruments.template.initial_pitch_tooltip_template"],
        )
        self._channel_labels: Dict[ChannelName, str] = {
            channel_name: channel_label(language_manager, channel_name) for channel_name in ChannelName.items()
        }

        super().__init__(
            tag=TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
        )

        self._enable_horizontal_collapse(
            initial_collapsed=initial_collapsed,
            side=CollapseAxis.HORIZONTAL_RIGHT,
        )

    def create_panel(self, parent: str) -> None:
        with (
            card(
                parent,
                self.tag,
                auto_resize_y=False,
                height=-1,
                no_scrollbar=True,
            ),
            self._collapsible_section(
                self._language_manager["reconstructions.instruments.label.section"],
                glyph=self._glyphs.headers.instruments,
            ),
        ):
            self._create_content()

        self._setup_mouse_event_handler()

    def _create_content(self) -> None:
        dpg.add_text(
            tag=self.no_data_message_tag,
            parent=self._body_container,
            default_value=self._language_manager["global.dialog.message.reconstruction_no_data"],
            show=True,
        )

        with dpg.group(
            tag=self.sample_size_group_tag,
            parent=self._body_container,
            show=False,
        ):
            self._create_size_field(
                self._lbl_sample_size,
                self.sample_size_tag,
                self.sample_size_group_tag,
            )

        with dpg.tab_bar(
            tag=self.tab_bar_tag,
            parent=self._body_container,
            show=False,
        ):
            self._create_tabs_for_generators()

    def _create_size_field(
        self,
        label: str,
        value_tag: str,
        parent: str,
    ) -> None:
        """Draws a read-only byte figure, styled as the pitch stepper's readout is.

        The figure names how much of the NES data area an export spends, so it reads as
        information beside the fields that change: the label column aligns with the stepper
        below it, and the value carries the stepper's own read-only colour and font. A tooltip
        names the export the figure measures, since the formats spend differently.
        """
        with labeled_field(
            label,
            self._pitch_stepper_style.dimensions.label_width,
            parent=parent,
        ):
            dpg.add_text(tag=value_tag, default_value="")
            dpg_set_palette_color(value_tag, self._pitch_stepper_style.value_color)
            FontRegistry.bind_to_item(value_tag, Font.MONO)

        show_tooltip(
            value_tag,
            self._tip_size_bytes,
            tag=compose_tag(value_tag, SUF_TOOLTIP),
        )

    def _get_generator_tab_tag(self, channel_name: ChannelName) -> str:
        return compose_tag(self.tab_bar_tag, channel_name)

    def _get_instrument_size_tag(self, channel_name: ChannelName) -> str:
        return compose_tag(
            self.tab_bar_tag,
            channel_name,
            SUF_RECONSTRUCTIONS_INSTRUMENTS_INSTRUMENT_SIZE,
        )

    def _get_window_tag(self, tab_tag: str) -> str:
        return compose_tag(tab_tag, SUF_RECONSTRUCTIONS_INSTRUMENTS_WINDOW)

    def _get_feature_group_tag(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
    ) -> str:
        return compose_tag(self.tab_bar_tag, channel_name, feature_key, SUF_GROUP)

    def _get_feature_text_group_tag(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
    ) -> str:
        return compose_tag(self.tab_bar_tag, channel_name, feature_key, SUF_GRAPH_RAW_DATA)

    def _get_feature_text_tag(self, text_group_tag: str) -> str:
        return compose_tag(text_group_tag, SUF_TEXT)

    def _get_feature_plot_tag(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
    ) -> str:
        return compose_tag(self.tab_bar_tag, channel_name, feature_key, SUF_GRAPH)

    def _setup_mouse_event_handler(self) -> None:
        with dpg.handler_registry(tag=self.mouse_item_handler_tag):
            dpg.add_mouse_move_handler(callback=self._on_mouse_move)

    def _export_callback(self, channel_name: ChannelName) -> VoidCallback:
        """The press handler for one channel's export button.
        the channel is captured in a closure, which carries one.
        """
        return lambda: self.call(self.on_instrument_export, channel_name)

    def _create_tabs_for_generators(self) -> None:
        for channel_name in ChannelName.items():
            self._create_generator_tab(channel_name)

    def _generator_kind(
        self,
        channel_name: ChannelName,
    ) -> LibraryGeneratorName:
        return CHANNEL_GENERATOR_KIND[channel_name]

    def _generator_features(
        self,
        channel_name: ChannelName,
    ) -> List[FeatureKey]:
        return supported_features(self._generator_kind(channel_name))

    def _feature_plot_config(self, channel_name: ChannelName, feature_key: FeatureKey) -> FeaturePlotConfig:
        return self._feature_plot_configs[self._generator_kind(channel_name)][feature_key]

    def _create_generator_tab(self, channel_name: ChannelName) -> None:
        tab_tag = self._get_generator_tab_tag(channel_name)
        window_tag = self._get_window_tag(tab_tag)

        with dpg.tab(
            label=self._channel_labels[channel_name],
            tag=tab_tag,
            parent=self.tab_bar_tag,
            show=False,
        ):
            self.channel_plots[channel_name] = {}
            button_tag = compose_tag(TAG_RECONSTRUCTIONS_INSTRUMENTS_BUTTON_EXPORT_INSTRUMENT, tab_tag)
            self._export_buttons[channel_name] = GUIButton(
                tag=button_tag,
                parent=tab_tag,
                label=self._language_manager["reconstructions.instruments.label.export_instrument_button"],
                width=-1,
                callback=self._export_callback(channel_name),
            )
            self._status_bar.bind_to_item(
                button_tag,
                self._language_manager["reconstructions.instruments.message.status_export_instrument"].format(
                    channel=self._channel_labels[channel_name]
                ),
            )

            with dpg.child_window(
                tag=window_tag,
                parent=tab_tag,
                height=-1,
            ):
                self._create_generator_content(channel_name, window_tag)

            ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_INSTRUMENT).bind_to_item(window_tag)

        ThemeRegistry.get(TAG_GLOBAL_THEME_INSTRUMENT_TABS).bind_to_item(tab_tag)

    def _create_generator_content(
        self,
        channel_name: ChannelName,
        window_tag: str,
    ) -> None:
        initial_pitch = self._default_initial_pitch(channel_name)
        self._create_size_field(
            self._lbl_instrument_size,
            self._get_instrument_size_tag(channel_name),
            window_tag,
        )
        self._create_pitch_stepper(channel_name, initial_pitch, window_tag)
        self._create_generator_feature_displays(channel_name, window_tag)

    def _default_initial_pitch(self, channel_name: ChannelName) -> int:
        return resting_reference(channel_name)

    def _create_generator_feature_displays(
        self,
        channel_name: ChannelName,
        window_tag: str,
    ) -> None:
        for feature_key in self._generator_features(channel_name):
            self._add_generator_feature_display(
                channel_name,
                feature_key,
                window_tag,
            )

    def _add_generator_feature_display(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        window_tag: str,
    ) -> None:
        feature_group_tag = self._get_feature_group_tag(
            channel_name,
            feature_key,
        )
        with dpg.group(
            tag=feature_group_tag,
            parent=window_tag,
        ):
            dpg.add_separator(parent=window_tag)
            feature_data_array = np.empty(0, dtype=np.int8)
            plot = self._create_feature_display(
                channel_name,
                feature_key,
                feature_data_array,
                feature_group_tag,
            )
            self.channel_plots[channel_name][feature_key] = plot

    def _apply_pitch_display(
        self,
        channel_name: ChannelName,
        value: int,
    ) -> None:
        stepper = self._pitch_steppers.get(channel_name)
        if stepper is not None:
            stepper.set_value(value)

    def _update_generator_plot(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        plots = self.channel_plots.get(channel_name)
        if plots is None:
            return

        plot = plots.get(feature_key)
        if plot is None:
            return

        config = self._feature_plot_config(channel_name, feature_key)
        self._configure_plot_data(
            plot,
            channel_name,
            feature_key,
            config,
            data,
        )

    def _update_raw_data_text(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
    ) -> None:
        text_group_tag = self._get_feature_text_group_tag(
            channel_name,
            feature_key,
        )
        raw_data_tag = self._get_feature_text_tag(text_group_tag)
        raw_data_text = self._format_data(data)
        dpg_set_value(raw_data_tag, raw_data_text)
        self._apply_input_theme(channel_name, feature_key, len(data))

    def update_view(
        self,
        view_model: ReconstructionInstrumentsViewModel,
    ) -> None:
        """Shows a tab per channel, marking the ones standing by.

        Every channel is editable for as long as a reconstruction is open, so writing an
        envelope into a channel standing by is what puts it in play. A muted tab label and a
        withheld export say which channels are there.
        """
        is_loaded = view_model.reconstruction_loaded
        dpg_configure_item(self.no_data_message_tag, show=not is_loaded)
        dpg_configure_item(self.tab_bar_tag, show=is_loaded)
        dpg_configure_item(self.sample_size_group_tag, show=is_loaded)
        self._update_sizes(view_model.footprint)

        for channel_name in ChannelName.items():
            tab_tag = self._get_generator_tab_tag(channel_name)
            dpg_configure_item(tab_tag, show=is_loaded)
            self._apply_playing_state(
                channel_name,
                channel_name in view_model.playing_channels,
            )

    def _apply_playing_state(
        self,
        channel_name: ChannelName,
        is_playing: bool,
    ) -> None:
        """Marks one channel's tab as playing or standing by.

        The muted theme reaches the tab label alone; the tab's body carries its own text colour,
        so a channel standing by stays as readable to edit as one that plays.
        """
        theme_tag = TAG_GLOBAL_THEME_INSTRUMENT_TABS if is_playing else TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED
        ThemeRegistry.get(theme_tag).bind_to_item(self._get_generator_tab_tag(channel_name))

        export_button = self._export_buttons.get(channel_name)
        if export_button is not None:
            export_button.set_enabled(is_playing)

    def _update_sizes(
        self,
        footprint: Optional[SampleFootprintViewModel],
    ) -> None:
        """Writes the byte figures the loaded reconstruction occupies, the sample's and each channel's.

        A channel standing by is written by no export, so it reads as the nothing it costs.
        """
        if footprint is None:
            return

        dpg_set_value(self.sample_size_tag, self._format_size(footprint.total_bytes))
        for channel_name in ChannelName.items():
            instrument_bytes = footprint.bytes_for(channel_name)
            dpg_set_value(
                self._get_instrument_size_tag(channel_name),
                self._format_size(instrument_bytes if instrument_bytes is not None else 0),
            )

    def _format_size(self, byte_count: int) -> str:
        return self._tpl_size_bytes.format(bytes=byte_count)

    def update_feature_data(
        self,
        generators: Optional[Dict[ChannelName, Features]],
    ) -> None:
        if generators is None:
            return

        for channel_name in ChannelName.items():
            generator_features = generators.get(channel_name)
            if generator_features is None:
                continue

            self._update_generator_feature_data(
                channel_name,
                generator_features,
            )

    def _update_generator_feature_data(
        self,
        channel_name: ChannelName,
        generator_features: Features,
    ) -> None:
        initial_pitch = cast(int, generator_features[FeatureKey.INITIAL_PITCH])
        self._apply_pitch_display(channel_name, initial_pitch)

        for feature_key in self._generator_features(channel_name):
            self._update_generator_feature_display(
                channel_name,
                generator_features,
                feature_key,
            )

    def _update_generator_feature_display(
        self,
        channel_name: ChannelName,
        generator_features: Features,
        feature_key: FeatureKey,
    ) -> None:
        feature = self._feature_array(generator_features, feature_key)
        self._update_generator_plot(channel_name, feature_key, feature)
        self._update_raw_data_text(channel_name, feature_key, feature)

    def _feature_array(
        self,
        generator_features: Features,
        feature_key: FeatureKey,
    ) -> np.ndarray:
        feature = cast(Optional[np.ndarray], generator_features.get(feature_key))
        if feature is None:
            return np.array([], dtype=np.int8)
        return feature

    def _pitch_kind(self, channel_name: ChannelName) -> PitchValueKind:
        return PERIOD_VALUE_KIND if channel_name == ChannelName.NOISE else PITCH_VALUE_KIND

    def _create_pitch_stepper(
        self,
        channel_name: ChannelName,
        initial_pitch: int,
        parent: str,
    ) -> None:
        is_noise = channel_name == ChannelName.NOISE
        kind = self._pitch_kind(channel_name)
        stepper = GUIPitchStepper(
            tag=parent,
            parent=parent,
            kind=kind,
            initial_value=initial_pitch,
            label=(
                self._language_manager["reconstructions.instruments.label.initial_period"]
                if is_noise
                else self._language_manager["reconstructions.instruments.label.initial_pitch"]
            ),
            tooltip=self._pitch_tooltips.for_kind(kind),
            status_message=(
                self._language_manager["reconstructions.instruments.message.status_input_period"]
                if is_noise
                else self._language_manager["reconstructions.instruments.message.status_input_pitch"]
            ),
            status_bar=self._status_bar,
            layout=self._pitch_stepper_style.dimensions,
            plus_minus_layout=self._pitch_stepper_style.plus_minus,
            value_color=self._pitch_stepper_style.value_color,
        )
        stepper.on_value_changed = partial(
            self._on_pitch_value_changed,
            channel_name,
        )
        self._pitch_steppers[channel_name] = stepper

    def _on_pitch_value_changed(
        self,
        channel_name: ChannelName,
        value: int,
    ) -> None:
        self.call(self.on_pitch_value_changed, channel_name, value)

    def _on_mouse_move(self, _sender: Sender, _app_data: Tuple[int, int]) -> None:
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
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
        parent: str,
    ) -> GUIBarGraph:
        config = self._feature_plot_config(channel_name, feature_key)
        plot = self._add_bar_plot(
            parent,
            config,
            data,
            channel_name,
            feature_key,
        )
        self._add_raw_data_text(
            parent,
            channel_name,
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
        channel_name: ChannelName,
        feature_key: FeatureKey,
    ) -> GUIBarGraph:
        plot_tag = self._get_feature_plot_tag(channel_name, feature_key)
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
            channel_name,
            feature_key,
            config,
            data,
        )

        return plot

    def _configure_plot_data(
        self,
        plot: GUIBarGraph,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        config: FeaturePlotConfig,
        data: np.ndarray,
    ) -> None:
        self._load_plot_data(plot, channel_name, feature_key, config, data)
        plot.set_callbacks(
            on_bar_point_clicked=lambda data: self._on_bar_point_clicked(
                channel_name,
                feature_key,
                data,
                plot.plot_tag,
            ),
            on_bar_point_hovered=self._on_bar_point_hovered,
        )

    def _on_bar_point_clicked(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        data: np.ndarray,
        plot_tag: str,
    ) -> None:
        raw_data_tag = compose_tag(plot_tag, SUF_GRAPH_RAW_DATA)
        dpg_set_value(raw_data_tag, self._format_data(data))
        self.call(self.on_bar_data_changed, channel_name, feature_key, data)

    def _on_bar_point_hovered(
        self,
        label: Optional[str],
        index: Optional[int],
    ) -> None:
        self.call(self.on_reconstruction_instrument_hovered, index)
        if label is not None:
            self._status_bar.set(
                self._language_manager["reconstructions.instruments.message.status_bar"].format(
                    instrument_feature=label
                )
            )

    def _add_raw_data_text(
        self,
        parent: str,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        config: FeaturePlotConfig,
        plot: GUIBarGraph,
        data: np.ndarray,
    ) -> None:
        text_group_tag = self._get_feature_text_group_tag(
            channel_name,
            feature_key,
        )
        raw_data_text = self._format_data(data)
        raw_data_tag = self._get_feature_text_tag(text_group_tag)
        copy_button_tag = compose_tag(text_group_tag, SUF_BUTTON_COPY)

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
                    channel_name,
                    feature_key,
                    config,
                    plot,
                ),
            )
            FontRegistry.bind_to_item(raw_data_tag, Font.MONO)

        self._status_bar.bind_to_item(
            copy_button_tag,
            self._language_manager["reconstructions.instruments.message.status_copy_sequence"],
        )
        self._status_bar.bind_to_item(
            raw_data_tag,
            partial(self._sequence_status_message, channel_name, feature_key),
        )

    def _sequence_status_message(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        *_args: Any,
        **_kwargs: Any,
    ) -> str:
        """Describes the sequence input, naming the export limit once a sequence passes it."""
        item_count = self._sequence_lengths.get((channel_name, feature_key), 0)
        if item_count > MAX_SEQUENCE_ITEMS:
            return self._language_manager["reconstructions.instruments.message.status_sequence_too_long"].format(
                instrument_feature=feature_key.capitalized,
                items=item_count,
                limit=MAX_SEQUENCE_ITEMS,
            )

        return self._language_manager["reconstructions.instruments.message.status_sequence"].format(
            instrument_feature=feature_key.capitalized
        )

    def _apply_input_theme(
        self,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        item_count: int,
    ) -> None:
        """Colours the sequence input by how a FamiTracker export treats its length.

        A sequence longer than ``MAX_SEQUENCE_ITEMS`` exports its opening items, so the
        input carries the warning colour to show which part of the envelope reaches a
        FamiTracker file.
        """
        self._sequence_lengths[(channel_name, feature_key)] = item_count
        text_group_tag = self._get_feature_text_group_tag(channel_name, feature_key)
        raw_data_tag = self._get_feature_text_tag(text_group_tag)
        theme = self.warning_input_theme if item_count > MAX_SEQUENCE_ITEMS else self.theme
        theme.bind_to_item(raw_data_tag)

    def _parse_raw_data_input(
        self,
        sender: Sender,
        app_data: str,
        user_data: Tuple[ChannelName, FeatureKey, FeaturePlotConfig, GUIBarGraph],
    ) -> None:
        channel_name, feature_key, config, plot = user_data
        data_range = config.data_range if config.data_range is not None else (-128, 127)

        try:
            raw_data_items = app_data.strip().split()
            raw_data = np.array(
                [clamp(int(value), *data_range) for value in raw_data_items],
                dtype=np.int8,
            )
        except ValueError:
            logger.error(f"Invalid {channel_name.name} data input for {feature_key.name}: {app_data}")
            self.invalid_input_theme.bind_to_item(sender)
            return

        self._apply_input_theme(channel_name, feature_key, len(raw_data))
        dpg.set_value(sender, self._format_data(raw_data))
        self.call(self.on_raw_data_changed, channel_name, feature_key, raw_data)
        self._load_plot_data(plot, channel_name, feature_key, config, raw_data)

    def _format_data(self, data: np.ndarray) -> str:
        string_data = [str(clamp(int(value), -128, 127)) for value in data]
        return " ".join(string_data)

    def _load_plot_data(
        self,
        plot: GUIBarGraph,
        channel_name: ChannelName,
        feature_key: FeatureKey,
        config: FeaturePlotConfig,
        data: np.ndarray,
    ) -> None:
        _, _, y_ticks = self._calculate_plot_limits(config, data)
        name = f"{channel_name.capitalize()}: {feature_key.capitalized}"
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
            copied_label=self._language_manager["global.dialog.label.copied"],
        )
