from typing import Any, Callable, Dict, Optional, Tuple, cast

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalMessageElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionsDetailsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
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
    TAG_TAB_GLOBAL_RECONSTRUCTIONS,
)
from sampletones_application.constants.graphs import (
    SUF_GRAPH,
    SUF_GRAPH_RAW_DATA,
)
from sampletones_application.constants.reconstructions import (
    SUF_RECONSTRUCTIONS_DETAILS_WINDOW,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_NO_DATA_MESSAGE,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_SEPARATOR,
    TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTI,
    TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
    TAG_PANEL_RECONSTRUCTIONS_DETAILS,
    TAG_TAB_BAR_RECONSTRUCTIONS_DETAILS,
    TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS,
)
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.reconstructions import ReconstructionsLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs.bar import GUIBarGraph
from sampletones_application.ui.elements.graphs.utils import extend_y_range
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.reconstruction.details.config import (
    FEATURE_DISPLAY_ORDER,
    FeaturePlotConfig,
    make_feature_plot_configs,
)
from sampletones_application.ui.themes.default import DefaultTheme
from sampletones_application.ui.themes.input import InvalidInputTheme
from sampletones_application.ui.themes.tables.initial_pitch import (
    InitialPitchTableTheme,
)
from sampletones_application.utils.clipboard import copy_to_clipboard
from sampletones_application.utils.dpg import (
    dpg_configure_item,
    dpg_delete_item,
    dpg_set_value,
)
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.tooltip import show_tooltip
from sampletones_application.view_model.reconstruction.details import (
    ReconstructionDetailsViewModel,
)
from sampletones_application.view_model.reconstruction.feature import (
    FeatureData,
)
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.constants.general import MAX_PERIOD, MIN_PITCH
from sampletones_core.utils.frequencies import (
    NAME_TO_PERIOD,
    NAME_TO_PITCH,
    period_to_name,
    pitch_to_name,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.arrays import clamp

OnInstrumentExportCallback = Callable[[GeneratorName], None]
OnReconstructionInstrumentHoveredCallback = Callable[[Optional[int]], None]


class GUIReconstructionDetailsPanel(GUIPanel):
    def __init__(
        self,
        shortcut_manager: ShortcutManager,
        *,
        layout_general: GeneralLayout,
        layout_graphs: GraphsLayout,
        layout_reconstructions: ReconstructionsLayout,
        language_manager: LanguageManager,
    ) -> None:
        self.shortcut_manager = shortcut_manager

        self.generator_plots: Dict[GeneratorName, Dict[FeatureKey, GUIBarGraph]] = {}

        self.tab_bar_tag = TAG_TAB_BAR_RECONSTRUCTIONS_DETAILS
        self.no_data_message_tag = f"{self.tab_bar_tag}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_NO_DATA_MESSAGE}"
        self.export_button_separator_tag = f"{self.tab_bar_tag}{SUF_RECONSTRUCTIONS_RECONSTRUCTION_SEPARATOR}"
        self.mouse_item_handler_tag = f"{TAG_PANEL_RECONSTRUCTIONS_DETAILS}{SUF_HANDLER_REGISTRY}"

        self._graphs: Dict[str, GUIBarGraph] = {}
        self._layout_general = layout_general
        self._layout_graphs = layout_graphs
        self._layout_reconstructions = layout_reconstructions
        self._feature_plot_configs = make_feature_plot_configs(layout_reconstructions, language_manager)

        self.theme = DefaultTheme()
        self.invalid_input_theme = InvalidInputTheme()
        self.initial_pitch_theme = InitialPitchTableTheme()

        self.on_instrument_export: Optional[OnInstrumentExportCallback] = None
        self.on_instruments_export: Optional[VoidCallback] = None
        self.on_reconstruction_instrument_hovered: Optional[OnReconstructionInstrumentHoveredCallback] = None

        self.on_pitch_input: Optional[Callable[[GeneratorName, str, int], None]] = None
        self.on_pitch_step: Optional[Callable[[GeneratorName, int], None]] = None
        self.on_hold_tick: Optional[Callable[[bool, bool, float, GeneratorName], None]] = None
        self.on_hold_ended: Optional[VoidCallback] = None
        self.on_bar_data_changed: Optional[Callable[[GeneratorName, FeatureKey, np.ndarray], None]] = None
        self.on_raw_data_changed: Optional[Callable[[GeneratorName, FeatureKey, np.ndarray], None]] = None

        self._lbl_section = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                ReconstructionsDetailsElements.RECONSTRUCTION_DETAILS,
            )
        ]
        self._lbl_export_fti = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                ReconstructionsDetailsElements.EXPORT_FTI_BUTTON,
            )
        ]
        self._lbl_export_ftis = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                ReconstructionsDetailsElements.EXPORT_FTIS_BUTTON,
            )
        ]
        self._lbl_copy = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                ReconstructionsDetailsElements.COPY_BUTTON,
            )
        ]
        self._lbl_generators = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                ReconstructionsDetailsElements.GENERATORS_TEXT,
            )
        ]
        self._lbl_initial_period = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                ReconstructionsDetailsElements.INITIAL_PERIOD,
            )
        ]
        self._lbl_initial_pitch = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.LABEL,
                ReconstructionsDetailsElements.INITIAL_PITCH,
            )
        ]
        self._msg_input_pitch = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.MESSAGE,
                ReconstructionsDetailsElements.STATUS_INPUT_PITCH,
            )
        ]
        self._msg_input_period = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.MESSAGE,
                ReconstructionsDetailsElements.STATUS_INPUT_PERIOD,
            )
        ]
        self._msg_bar = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.MESSAGE,
                ReconstructionsDetailsElements.STATUS_BAR,
            )
        ]
        self._msg_sequence = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.MESSAGE,
                ReconstructionsDetailsElements.STATUS_SEQUENCE,
            )
        ]
        self._msg_copy_sequence = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.MESSAGE,
                ReconstructionsDetailsElements.STATUS_COPY_SEQUENCE,
            )
        ]
        self._tpl_pitch_tooltip = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.TEMPLATE,
                ReconstructionsDetailsElements.INITIAL_PITCH_TOOLTIP_TEMPLATE,
            )
        ]
        self._msg_reconstruction_no_data = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.MESSAGE,
                GlobalMessageElements.RECONSTRUCTION_NO_DATA,
            )
        ]
        self._lbl_copied = language_manager[TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.COPIED)]

        super().__init__(
            tag=TAG_PANEL_RECONSTRUCTIONS_DETAILS,
            parent=f"{TAG_TAB_GLOBAL_RECONSTRUCTIONS}{SUF_PANEL_RIGHT}",
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
        section_text = dpg.add_text(self._lbl_section)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
            label=self._lbl_export_ftis,
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
            default_value=self._msg_reconstruction_no_data,
            show=True,
        )

        dpg.add_text(
            self._lbl_generators,
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
                label=self._lbl_export_fti,
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

    def _apply_pitch_display(self, generator_name: GeneratorName, value: int) -> None:
        window_tag = self._get_window_tag(self._get_generator_tab_tag(generator_name))
        input_tag = f"{window_tag}{SUF_INPUT}"
        value_tag = f"{input_tag}{SUF_TEXT}"
        _, display_value = self._format_initial_pitch(generator_name, value)
        dpg_set_value(input_tag, display_value)
        dpg_set_value(value_tag, str(value))

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

        config = self._feature_plot_configs[feature_key]
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

    def update_view(self, viewmodel: ReconstructionDetailsViewModel) -> None:
        is_loaded = viewmodel.reconstruction_loaded
        dpg_configure_item(self.export_button_separator_tag, show=is_loaded)
        dpg_configure_item(self.no_data_message_tag, show=not is_loaded)
        dpg_configure_item(self.tab_bar_tag, show=is_loaded)
        dpg_configure_item(
            TAG_BUTTON_RECONSTRUCTIONS_DETAILS_EXPORT_FTIS,
            show=is_loaded,
            enabled=is_loaded,
        )
        dpg_configure_item(TAG_TEXT_RECONSTRUCTIONS_DETAILS_GENERATORS, show=is_loaded)

        for generator_name in GeneratorName.items():
            tab_tag = self._get_generator_tab_tag(generator_name)
            is_available = generator_name in viewmodel.available_generators
            dpg_configure_item(tab_tag, show=is_available)

    def update_feature_data(self, feature_data: Optional[FeatureData]) -> None:
        if feature_data is None:
            return

        for generator_name in GeneratorName.items():
            if generator_name not in feature_data.generators:
                continue

            generator_features = feature_data.get_generator_features(generator_name)
            if generator_features is None:
                continue

            initial_pitch = cast(int, generator_features[FeatureKey.INITIAL_PITCH])
            self._apply_pitch_display(generator_name, initial_pitch)

            for key in FEATURE_DISPLAY_ORDER:
                if key == FeatureKey.INITIAL_PITCH:
                    continue

                feature: Optional[np.ndarray] = cast(Optional[np.ndarray], generator_features.get(key))
                if feature is None:
                    feature = np.array([], dtype=np.int8)

                self._update_generator_plot(generator_name, key, feature)
                self._update_raw_data_text(generator_name, key, feature)

    def update_pitch(self, generator_name: GeneratorName, new_pitch: int) -> None:
        self._apply_pitch_display(generator_name, new_pitch)

    def _format_initial_pitch(self, generator_name: GeneratorName, initial_pitch: int) -> Tuple[str, str]:
        if generator_name == GeneratorName.NOISE:
            label = self._lbl_initial_period
            display_value = period_to_name(initial_pitch)
        else:
            label = self._lbl_initial_pitch
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
        pitch_table = self._layout_reconstructions.initial_pitch_table
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
                width=pitch_table.label_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=pitch_table.label_width,
            )
            dpg.add_table_column(
                width=pitch_table.display_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=pitch_table.display_width,
            )
            dpg.add_table_column(width_stretch=True)
            dpg.add_table_column(
                width=pitch_table.button_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=pitch_table.button_width,
            )
            dpg.add_table_column(
                width=pitch_table.button_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=pitch_table.button_width,
            )
            with dpg.table_row():
                with dpg.table_cell():
                    dpg.add_text(label, tag=input_label_tag)
                with dpg.table_cell():
                    dpg.add_text(
                        str(initial_pitch),
                        tag=value_tag,
                        color=self._layout_general.colors.text.disabled,
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
                        label="-",
                        tag=decrement_button_tag,
                        width=self._layout_general.buttons.int_width,
                        callback=self._change_initial_pitch,
                        user_data=(
                            generator_name,
                            -1,
                        ),
                    )

                with dpg.table_cell():
                    GUIButton(
                        label="+",
                        tag=increment_button_tag,
                        width=self._layout_general.buttons.int_width,
                        callback=self._change_initial_pitch,
                        user_data=(
                            generator_name,
                            1,
                        ),
                    )

        self.initial_pitch_theme.bind_to_item(table_tag)
        self._create_initial_pitch_tooltip(generator_name, input_tag)
        status_message = self._msg_input_pitch if generator_name != GeneratorName.NOISE else self._msg_input_period
        GUIStatusBar.bind_to_item(input_tag, status_message)

        self.shortcut_manager.setup_input_focus_handlers(input_tag)
        self._setup_button_hold_handlers(
            decrement_button_tag,
            increment_button_tag,
            generator_name,
        )

    def _setup_button_hold_handlers(
        self,
        decrement_button_tag: str,
        increment_button_tag: str,
        generator_name: GeneratorName,
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
        user_data: Tuple[str, str, GeneratorName],
    ) -> None:
        decrement_button_tag, increment_button_tag, generator_name = user_data
        if not dpg.does_item_exist(decrement_button_tag) or not dpg.does_item_exist(increment_button_tag):
            dpg_delete_item(sender)
            return

        is_decrement = dpg.is_item_hovered(decrement_button_tag)
        is_increment = dpg.is_item_hovered(increment_button_tag)
        if not is_decrement and not is_increment:
            return

        self.call(
            self.on_hold_tick,
            is_decrement,
            is_increment,
            dpg.get_delta_time(),
            generator_name,
        )

    def _on_mouse_release(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self.call(self.on_hold_ended)

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
            example_name = "4-#"
            example_value = NAME_TO_PERIOD[example_name]
        else:
            pitch_type = "pitch"
            example_name = "C-4"
            example_value = NAME_TO_PITCH[example_name]

        show_tooltip(
            input_tag,
            self._tpl_pitch_tooltip.format(
                pitch_type,
                example_name,
                example_value,
            ),
        )

    def _change_initial_pitch(
        self,
        sender: Sender,
        app_data: int,
        user_data: Tuple[GeneratorName, int],
    ) -> None:
        if user_data is None:
            return
        generator_name, direction = user_data
        self.call(self.on_pitch_step, generator_name, direction)

    def _validate_and_update_initial_pitch_input(
        self,
        sender: Sender,
        app_data: str,
        user_data: Tuple[GeneratorName, str, str],
    ) -> None:
        generator_name, _, value_tag = user_data
        self.call(
            self.on_pitch_input,
            generator_name,
            app_data,
            int(dpg.get_value(value_tag)),
        )

    def _create_feature_display(
        self,
        generator_name: GeneratorName,
        feature_key: FeatureKey,
        data: np.ndarray,
        parent: str,
    ) -> GUIBarGraph:
        config = self._feature_plot_configs[feature_key]
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

    def _on_bar_point_hovered(self, label: Optional[str], index: Optional[int]) -> None:
        self.call(self.on_reconstruction_instrument_hovered, index)
        if label is not None:
            GUIStatusBar.set(self._msg_bar.format(instrument_feature=label))

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
                label=self._lbl_copy,
                width=self._layout_general.buttons.copy_width,
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
        GUIStatusBar.bind_to_item(copy_button_tag, self._msg_copy_sequence)
        GUIStatusBar.bind_to_item(
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
        copy_to_clipboard(text, self._lbl_copy, button_tag, copied_label=self._lbl_copied)
