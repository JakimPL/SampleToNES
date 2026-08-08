from typing import Any, Callable, List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_CHANNEL_NOISE,
    TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    TAG_GLOBAL_THEME_CHANNEL_PULSE2,
    TAG_GLOBAL_THEME_CHANNEL_TRIANGLE,
)
from sampletones_application.tags.reconstructions import (
    PRE_RECONSTRUCTION_GENERATOR,
    SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUTOSCALE,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_GENERATORS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_RECONSTRUCTION_WAVEFORM,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.reconstruction.reconstruction import (
    ReconstructionViewModel,
)
from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.constants.enums import AudioSourceType, GeneratorName
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback

_GENERATOR_THEME_TAGS = {
    GeneratorName.PULSE1: TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    GeneratorName.PULSE2: TAG_GLOBAL_THEME_CHANNEL_PULSE2,
    GeneratorName.TRIANGLE: TAG_GLOBAL_THEME_CHANNEL_TRIANGLE,
    GeneratorName.NOISE: TAG_GLOBAL_THEME_CHANNEL_NOISE,
}


class GUIReconstructionPlotPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout_graphs: GraphsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout_graphs = layout_graphs
        self._status_bar = status_bar
        self._language_manager = language_manager

        self.waveform_display: GUIWaveformGraph
        self._frame_length: Optional[int] = None

        self.on_generators_changed: Optional[Callable[[List[GeneratorName]], None]] = None

        self.autoscale_tag = compose_tag(
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT, SUF_RECONSTRUCTIONS_RECONSTRUCTION_AUTOSCALE
        )

        super().__init__(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,
        )
        self._enable_vertical_collapse(
            initial_collapsed=initial_collapsed,
            auto_height=True,
        )

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._language_manager["reconstructions.reconstruction.label.waveform_label"],
            glyph=self._glyphs.headers.waveform,
            width=0,
            no_scrollbar=True,
        ):
            self._create_autoscale_checkbox()
            self._create_waveform_display()
            self._create_generator_checkboxes()
            self._create_tooltips()

    def update_view(self, view_model: ReconstructionViewModel) -> None:
        for generator_name in GeneratorName:
            tag = self._get_generator_checkbox_tag(generator_name)
            is_available = generator_name in view_model.available_generators
            dpg_configure_item(
                tag,
                enabled=is_available,
                default_value=is_available,
            )
            dpg_set_value(tag, is_available)
            if is_available:
                ThemeRegistry.get(_GENERATOR_THEME_TAGS[generator_name]).bind_to_item(tag)
            else:
                dpg.bind_item_theme(tag, 0)

    def load_waveform_data(
        self,
        waveform_data: WaveformData,
        generators: List[GeneratorName],
    ) -> None:
        self._frame_length = waveform_data.frame_length
        self.waveform_display.load_waveform_data(waveform_data, generators)

    def update_waveform_data(
        self,
        waveform_data: WaveformData,
        generators: List[GeneratorName],
    ) -> None:
        self.waveform_display.update_waveform_data(waveform_data, generators)

    def clear_waveform(self) -> None:
        self._frame_length = None
        self.waveform_display.clear()

    def set_waveform_top_source(self, audio_source: AudioSourceType) -> None:
        self.waveform_display.set_top_source(audio_source)

    def set_reconstruction_dimmed(self, dimmed: bool) -> None:
        self.waveform_display.set_reconstruction_dimmed(dimmed)

    def set_overlay(self, index: Optional[int]) -> None:
        if self._frame_length is None:
            return

        if index is None:
            self.waveform_display.set_overlay_range(0, 0)
            return

        start = index * self._frame_length
        end = start + self._frame_length
        self.waveform_display.set_overlay_range(start, end)

    def set_playback_position(self, position: int) -> None:
        self.waveform_display.set_position(position)

    def _create_autoscale_checkbox(self) -> None:
        dpg.add_checkbox(
            label=self._language_manager["reconstructions.reconstruction.label.autoscale_checkbox"],
            tag=self.autoscale_tag,
            parent=self._body_container,
            default_value=True,
            callback=self._on_autoscale_changed,
        )
        FontRegistry.bind_to_item(self.autoscale_tag, Font.REGULAR_SMALL)

    def _create_waveform_display(self) -> None:
        self.waveform_display = GUIWaveformGraph(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_RECONSTRUCTION_WAVEFORM,
            parent=self._body_container,
            layout=self._layout_graphs,
            language_manager=self._language_manager,
            status_bar=self._status_bar,
        )

    def _create_generator_checkboxes(self) -> None:
        generator_labels = {
            GeneratorName.PULSE1: self._language_manager["global.context.label.pulse_1"],
            GeneratorName.PULSE2: self._language_manager["global.context.label.pulse_2"],
            GeneratorName.TRIANGLE: self._language_manager["global.context.label.triangle"],
            GeneratorName.NOISE: self._language_manager["global.context.label.noise"],
        }

        with dpg.group(
            tag=TAG_RECONSTRUCTIONS_RECONSTRUCTION_GROUP_GENERATORS,
            parent=self._body_container,
            horizontal=True,
        ):
            for generator_name, label in generator_labels.items():
                tag = self._get_generator_checkbox_tag(generator_name)
                dpg.add_checkbox(
                    label=label,
                    tag=tag,
                    default_value=False,
                    enabled=False,
                    callback=self._on_generator_checkbox_changed,
                )

                self._status_bar.bind_to_item(
                    tag,
                    self._create_message_function_for_generator_checkbox(generator_name),
                )

    def _create_tooltips(self) -> None:
        show_tooltip(
            self.autoscale_tag,
            self._language_manager["reconstructions.reconstruction.tooltip.autoscale_tooltip"],
        )

    def _create_message_function_for_generator_checkbox(
        self,
        generator_name: GeneratorName,
    ) -> MessageCallback:
        tag = self._get_generator_checkbox_tag(generator_name)
        name = generator_name.capitalized

        def message_function(*_args: Any, **_kwargs: Any) -> str:
            if not dpg.is_item_enabled(tag):
                return self._language_manager[
                    "reconstructions.instruments.message.status_generator_not_available"
                ].format(generator_name=name)

            return self._language_manager["reconstructions.instruments.message.status_generator_toggle"].format(
                generator_name=name,
                on_or_off=(
                    self._language_manager["global.dialog.template.off"]
                    if dpg.get_value(tag)
                    else self._language_manager["global.dialog.template.on"]
                ),
            )

        return message_function

    @staticmethod
    def _get_generator_checkbox_tag(generator_name: GeneratorName) -> str:
        return compose_tag(PRE_RECONSTRUCTION_GENERATOR, generator_name.value)

    def _read_selected_generators(self) -> List[GeneratorName]:
        selected_generators: List[GeneratorName] = []
        for generator_name in GeneratorName:
            if dpg.get_value(self._get_generator_checkbox_tag(generator_name)):
                selected_generators.append(generator_name)

        return selected_generators

    def _on_generator_checkbox_changed(self) -> None:
        selected_generators = self._read_selected_generators()
        self.call(self.on_generators_changed, selected_generators)

    def _on_autoscale_changed(self, _sender: Sender, app_data: bool) -> None:
        self.waveform_display.set_autoscale(app_data)
