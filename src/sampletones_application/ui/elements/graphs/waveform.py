from enum import StrEnum
from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Tuple, Union

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones_application.categories.context import channel_letter
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors.channel import ChannelColors
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import (
    SUF_GRAPH_PLOT,
    SUF_GRAPH_SUBPLOTS,
    SUF_GRAPH_THEME,
    SUF_GRAPH_X_AXIS,
    SUF_GRAPH_Y_AXIS,
    SUF_HANDLER_MOUSE,
    SUF_RIBBON_LANE,
    SUF_WAVEFORM_OVERLAY,
    SUF_WAVEFORM_POSITION_INDICATOR,
    TAG_GLOBAL_GRAPH_THEME_INDICATOR,
    TAG_GLOBAL_GRAPH_THEME_OVERLAY,
)
from sampletones_application.ui.elements.graphs.clock import ClockTick, clock_ticks
from sampletones_application.ui.elements.graphs.gesture import PlotClickGesture
from sampletones_application.ui.elements.graphs.graph import GUIGraph
from sampletones_application.ui.elements.graphs.layers.array import ArrayLayer
from sampletones_application.ui.elements.graphs.layers.instruction import (
    InstructionLayer,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import (
    dpg_bind_item_theme,
    dpg_configure_item,
    dpg_delete_children,
    dpg_delete_item,
)
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.palette.dpg import dpg_add_palette_theme_color
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.utils.palette.colors.grayscale import GrayscaleColor
from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.constants.audio import START_OF_AUDIO
from sampletones_core.constants.enums import AudioSourceType, ChannelName
from sampletones_core.library import InstructionLibraryFragment
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.time import seconds_from_samples


class SeriesShade(StrEnum):
    """How strongly a waveform series is drawn, which decides the color its theme carries."""

    FULL = "full"
    DIMMED = "dimmed"


WAVEFORM_ROWS: Final[int] = 1 + len(ChannelName.items())
LANE_LETTER_POSITION: Final[float] = 0.5
SINGLE_COLUMN: Final[int] = 1
COLLAPSED_LANE_WEIGHT: Final[float] = 0.001


class GUIWaveformGraph(GUIGraph[Union[ArrayLayer, InstructionLayer]]):
    tag: str
    parent: str
    width: int
    height: int
    label: str

    def __init__(
        self,
        tag: str,
        parent: str,
        *,
        layout: GraphsLayout,
        channel_colors: ChannelColors,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ):
        self._language_manager = language_manager
        self._layout = layout
        self._channel_colors = channel_colors
        self._status_bar = status_bar

        self._lbl_waveform_original = language_manager["global.graph.label.waveform_original"]
        self._lbl_waveform_reconstruction = language_manager["global.graph.label.waveform_reconstruction"]
        self._msg_regenerating = language_manager["global.graph.message.waveform_regenerating"]

        self.reconstruction_autoscale = True
        self._reconstruction_dimmed: bool = False
        self._top_source: AudioSourceType = AudioSourceType.RECONSTRUCTION

        self.position_indicator_tag = compose_tag(tag, SUF_WAVEFORM_POSITION_INDICATOR)
        self.overlay_rectangle_tag = compose_tag(tag, SUF_WAVEFORM_OVERLAY)
        self.mouse_handler_tag = compose_tag(tag, SUF_HANDLER_MOUSE)

        self.on_position_clicked: Optional[Callable[[int], None]] = None
        self._click = PlotClickGesture(
            click_travel=layout.waveform.click_travel,
            on_clicked=self._on_plot_clicked,
        )

        self.subplots_tag = compose_tag(tag, SUF_GRAPH_SUBPLOTS)
        self.lane_plot_tags: Dict[ChannelName, str] = {
            channel_name: compose_tag(tag, SUF_RIBBON_LANE, channel_name.value, SUF_GRAPH_PLOT)
            for channel_name in ChannelName.items()
        }
        self.lane_y_axis_tags: Dict[ChannelName, str] = {
            channel_name: compose_tag(plot_tag, SUF_GRAPH_Y_AXIS)
            for channel_name, plot_tag in self.lane_plot_tags.items()
        }
        self._lane_heights: Dict[ChannelName, int] = {channel_name: 0 for channel_name in ChannelName.items()}

        self.indicator_theme = ThemeRegistry.get(TAG_GLOBAL_GRAPH_THEME_INDICATOR)
        self.overlay_theme = ThemeRegistry.get(TAG_GLOBAL_GRAPH_THEME_OVERLAY)

        self.current_data: Optional[Union[InstructionLibraryFragment[Any], WaveformData]] = None
        self._plays_what_it_draws = False
        self._sample_rate: int = 0
        self._named_span: Optional[Tuple[float, float, int]] = None
        self._series_themes: Dict[BaseColor, str] = {}
        self.current_position: int = 0

        _min_x = layout.graph.min_x
        _max_x = layout.graph.max_x
        _min_y = layout.graph.min_y
        _max_y = layout.graph.max_y

        super().__init__(
            tag,
            parent,
            layout.dimensions.width,
            layout.dimensions.height,
            "",
            (_min_x, _max_x),
            (_min_y, _max_y),
            layout.waveform.zoom_factor,
        )

    def _create_content(self) -> None:
        _min_y = self._layout.graph.min_y
        _max_y = self._layout.graph.max_y

        with (
            dpg.subplots(
                WAVEFORM_ROWS,
                SINGLE_COLUMN,
                tag=self.subplots_tag,
                parent=self.tag,
                width=self.width,
                height=self.height,
                row_ratios=[float(self.height), *([COLLAPSED_LANE_WEIGHT] * len(ChannelName.items()))],
                link_all_x=True,
                no_title=True,
                no_menus=True,
                no_resize=True,
            ),
            dpg.plot(
                label=self.label,
                tag=self.plot_tag,
                anti_aliased=True,
                no_mouse_pos=True,
                no_box_select=True,
                fit_button=dpg.mvMouseButton_Left,
                horizontal_mod=dpg.mvKey_LShift,
                pan_button=dpg.mvMouseButton_Left,
                zoom_rate=self.zoom_factor,
            ),
        ):
            dpg.add_plot_legend(
                tag=self.legend_tag,
                parent=self.plot_tag,
                location=dpg.mvPlot_Location_NorthEast,
            )
            dpg.add_plot_axis(
                dpg.mvXAxis,
                tag=self.x_axis_tag,
                parent=self.plot_tag,
                label=self._language_manager["global.graph.label.waveform_time_axis"],
                no_label=True,
            )
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.y_axis_tag,
                parent=self.plot_tag,
                label=self._language_manager["global.graph.label.waveform_amplitude_axis"],
            )
            self._add_position_indicator()
            self._set_overlay_rectangle()

        self._create_lane_rows()
        self._bind_event_handler()
        self._update_axes_limits()

    def _create_lane_rows(self) -> None:
        """A row per channel beneath the waveform, each marked with the letter it stands for.

        The rows share the subplot's grid, so a lane begins and ends where the waveform's span
        does however wide the amplitude labels beside them run, and each takes the waveform's
        stretch through the linked axis, so zooming and panning carry them together. A row of its
        own is what lets a lane print its channel's letter in that channel's color.
        """
        for channel_name, plot_tag in self.lane_plot_tags.items():
            with dpg.plot(
                tag=plot_tag,
                parent=self.subplots_tag,
                no_mouse_pos=True,
                no_box_select=True,
                no_menus=True,
                no_title=True,
                no_frame=True,
            ):
                dpg.add_plot_axis(
                    dpg.mvXAxis,
                    tag=compose_tag(plot_tag, SUF_GRAPH_X_AXIS),
                    parent=plot_tag,
                    no_label=True,
                    no_tick_labels=True,
                    no_tick_marks=True,
                    no_gridlines=True,
                )
                dpg.add_plot_axis(
                    dpg.mvYAxis,
                    tag=self.lane_y_axis_tags[channel_name],
                    parent=plot_tag,
                    no_label=True,
                    no_tick_marks=True,
                    no_gridlines=True,
                )
                dpg.set_axis_ticks(
                    self.lane_y_axis_tags[channel_name],
                    ((channel_letter(self._language_manager, channel_name), LANE_LETTER_POSITION),),
                )

            self._bind_lane_theme(channel_name, plot_tag)

    def _bind_lane_theme(self, channel_name: ChannelName, plot_tag: str) -> None:
        """Prints a lane's letter in the color the channel is drawn in everywhere else."""
        theme_tag = compose_tag(plot_tag, SUF_GRAPH_THEME)
        with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding, 0, 0, category=dpg.mvThemeCat_Plots)
            dpg_add_palette_theme_color(
                dpg.mvPlotCol_AxisText,
                self._channel_colors.for_channel(channel_name),
                category=dpg.mvThemeCat_Plots,
            )

        dpg_bind_item_theme(plot_tag, theme_tag)

    def set_height(self, height: int) -> None:
        """Gives the waveform the height asked for, keeping the row beneath it at its own.

        The plot stands in a grid, which takes its size from the container rather than from the
        plot, so the height a caller asks for reaches the grid and the two rows share it.
        """
        self.height = height
        self._resize_rows()

    def set_lane_heights(self, heights: Mapping[ChannelName, int]) -> None:
        """Gives each channel's row the height it needs, closing the ones with nothing to show."""
        self._lane_heights = {channel_name: heights.get(channel_name, 0) for channel_name in ChannelName.items()}
        self._resize_rows()

    def _resize_rows(self) -> None:
        """Hands the grid the room the waveform and the rows beneath it take together."""
        lanes = [
            float(self._lane_heights[channel_name]) or COLLAPSED_LANE_WEIGHT for channel_name in ChannelName.items()
        ]
        dpg_configure_item(
            self.subplots_tag,
            height=self.height + sum(self._lane_heights.values()),
            row_ratios=[float(self.height), *lanes],
        )

    def _setup_handlers(self) -> None:
        super()._setup_handlers()
        dpg.add_item_clicked_handler(
            button=dpg.mvMouseButton_Left,
            callback=self._click.press,
            parent=self.event_handler_tag,
        )
        with dpg.handler_registry(tag=self.mouse_handler_tag):
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._click.release,
            )

    def _on_plot_clicked(self, sample: float) -> None:
        """Reports the sample a click on the plot pointed at.

        A click names a sample of the audio a recording or an instruction plays, so it is reported
        while the graph draws the audio its player sounds.
        """
        if not self._plays_what_it_draws:
            return

        self.call(self.on_position_clicked, round(sample))

    def clear_layers(self) -> None:
        """Empties the plot of what it draws, which leaves a click nothing to sound until a load."""
        super().clear_layers()
        self._plays_what_it_draws = False

    def set_overlay_range(self, start: float = 0.0, end: float = 0.0) -> None:
        self._set_overlay_rectangle(x_start=start, x_end=end)

    def _on_hover(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        super()._on_hover(sender, app_data, user_data)
        FrameCallbackManager.set_frame_callback(self._restate_zoomed_clock_ticks)
        self._status_bar.set(
            self._msg_regenerating
            if self._reconstruction_dimmed
            else self._language_manager[
                (
                    "global.graph.message.waveform_playable_navigation"
                    if self._plays_what_it_draws
                    else "global.graph.message.waveform_navigation"
                )
            ]
        )

    def _set_overlay_rectangle(self, x_start: float = 0.0, x_end: float = 0.0) -> None:
        _min_y = self._layout.graph.min_y
        _max_y = self._layout.graph.max_y

        if not dpg.does_item_exist(self.overlay_rectangle_tag):
            dpg.add_shade_series(
                [x_start, x_end],
                y1=[_min_y, _min_y],
                y2=[_max_y, _max_y],
                tag=self.overlay_rectangle_tag,
                parent=self.y_axis_tag,
            )

            self.overlay_theme.bind_to_item(self.overlay_rectangle_tag)
        else:
            dpg.configure_item(
                self.overlay_rectangle_tag,
                x=[x_start, x_end],
                y1=[_min_y, _min_y],
                y2=[_max_y, _max_y],
            )

    def load_library_fragment(
        self,
        fragment: InstructionLibraryFragment[Any],
        color: BaseColor,
    ) -> None:
        """Draws one library fragment, in the color the generator that made it is known by.

        Args:
            fragment: The fragment to draw.
            color: The color the line is drawn in.
        """
        self.clear_layers()
        self.current_data = fragment
        self._plays_what_it_draws = True
        self.current_position = START_OF_AUDIO

        self.add_layer(
            InstructionLayer(
                data=fragment,
                name=self._language_manager["global.graph.label.waveform_sample_name"],
                color=color,
            )
        )

        self._update_axes_limits()
        self._update_position_indicator()

    def load_voice_waveform(
        self,
        audio: np.ndarray,
        *,
        name: str,
        color: BaseColor,
    ) -> None:
        """Draws one voice's own audio as a single series, in the color its generator is named by.

        A hand-written voice stands on no recording, so there is nothing to hold it against: the
        card shows what its envelopes make, labeled with the voice's own name. The series is the
        whole of what is drawn, so the controls that read a recording apply to nothing here.

        Args:
            audio: The waveform to draw.
            name: The name the series is labeled by.
            color: The color the line is drawn in.
        """
        self._reconstruction_dimmed = False
        self._sample_rate = 0
        self.clear_layers()
        self.add_layer(
            ArrayLayer(
                data=audio,
                name=name,
                color=color,
                max_display_points=self._layout.waveform.max_display_points,
            )
        )

    def _extract_reconstruction_layer_data(
        self,
        waveform_data: WaveformData,
        selected_channels: Optional[List[ChannelName]] = None,
    ) -> Tuple[Optional[np.ndarray], np.ndarray, float]:
        if selected_channels is None:
            selected_channels = list(waveform_data.approximations.keys())

        original_audio = waveform_data.original_audio
        approximation = waveform_data.partials(selected_channels)
        full_approximation = waveform_data.approximation

        if not self.reconstruction_autoscale or original_audio is None:
            return original_audio, approximation, 1.0

        original_audio = original_audio / waveform_data.coefficient

        coefficient = max(
            np.max(np.abs(full_approximation)),
            np.max(np.abs(original_audio)),
        )

        return original_audio, approximation, coefficient

    def _display_layers(
        self,
        waveform_data: WaveformData,
        selected_channels: Optional[List[ChannelName]] = None,
    ) -> List[Union[ArrayLayer, InstructionLayer]]:
        """Builds the ordered waveform layers for the current data.

        The original-audio layer joins the reconstruction layer only when the source audio is
        present, so a detached reconstruction or one whose source file is missing shows the
        approximation on its own.
        """
        original_audio, approximation_data, _ = self._extract_reconstruction_layer_data(
            waveform_data,
            selected_channels,
        )
        reconstruction_layer = self.reconstruction_layer(approximation_data)
        if original_audio is None:
            return [reconstruction_layer]

        sample_layer = self.sample_layer(original_audio)
        return self._ordered_layers(sample_layer, reconstruction_layer)

    def update_waveform_data(
        self,
        waveform_data: WaveformData,
        selected_channels: Optional[List[ChannelName]] = None,
    ) -> None:
        if not isinstance(self.current_data, WaveformData):
            return

        self.current_data = waveform_data
        for layer in self._display_layers(waveform_data, selected_channels):
            self.layers[layer.name] = layer

        self._update_display()

    def load_waveform_data(
        self,
        waveform_data: WaveformData,
        selected_channels: Optional[List[ChannelName]] = None,
    ) -> None:
        self._reconstruction_dimmed = False
        self.clear_layers()
        self.current_data = waveform_data
        self._sample_rate = waveform_data.sample_rate
        self._plays_what_it_draws = True
        for layer in self._display_layers(waveform_data, selected_channels):
            self.add_layer(layer)

        self._restate_clock_ticks(*self.x_range)

    def set_reconstruction_dimmed(self, dimmed: bool) -> None:
        """Grays the reconstruction line while its audio is being regenerated, restoring it when done.

        Only the reconstruction series is grayed; the original-audio series and the axes keep full
        strength, so the fade reads as "this waveform is being recomputed", and the status bar shows a
        regenerating hint for the same span. The state is remembered so an async data update arriving
        mid-regeneration redraws the reconstruction still grayed.
        """
        if self._reconstruction_dimmed == dimmed:
            return

        self._reconstruction_dimmed = dimmed
        self._status_bar.set(self._msg_regenerating if dimmed else "")

        layer = self.layers.get(self._lbl_waveform_reconstruction)
        if layer is None:
            return

        series_tag = self._series_tag(layer.name)
        if dpg.does_item_exist(series_tag):
            self._bind_series_theme(series_tag, layer)

    def reconstruction_layer(self, data: np.ndarray) -> ArrayLayer:
        return ArrayLayer(
            data=data,
            name=self._lbl_waveform_reconstruction,
            color=self._layout.colors.waveform_reconstruction,
            max_display_points=self._layout.waveform.max_display_points,
        )

    def sample_layer(self, data: np.ndarray) -> ArrayLayer:
        return ArrayLayer(
            data=data,
            name=self._lbl_waveform_original,
            color=self._layout.colors.waveform_sample,
            max_display_points=self._layout.waveform.max_display_points,
        )

    def _ordered_layers(
        self,
        sample_layer: Union[ArrayLayer, InstructionLayer],
        reconstruction_layer: Union[ArrayLayer, InstructionLayer],
    ) -> List[Union[ArrayLayer, InstructionLayer]]:
        """Orders the two waveform layers so the playback-selected source is drawn last.

        DearPyGui draws sibling series in child order, so the layer placed last renders
        on top. Returning the selected source last keeps the audible waveform in front.
        """
        if self._top_source == AudioSourceType.ORIGINAL:
            return [reconstruction_layer, sample_layer]

        return [sample_layer, reconstruction_layer]

    def set_top_source(self, audio_source: AudioSourceType) -> None:
        """Selects which waveform is drawn on top, following the playback source."""
        if audio_source == self._top_source:
            return

        self._top_source = audio_source
        if isinstance(self.current_data, WaveformData):
            self._reorder_series()

    def _reorder_series(self) -> None:
        if self._lbl_waveform_original not in self.layers:
            return

        sample_layer = self.layers[self._lbl_waveform_original]
        reconstruction_layer = self.layers[self._lbl_waveform_reconstruction]
        for layer in (sample_layer, reconstruction_layer):
            dpg_delete_item(self._series_tag(layer.name))

        self.layers.clear()
        for layer in self._ordered_layers(sample_layer, reconstruction_layer):
            self.layers[layer.name] = layer

        self._update_display()

    def clear(self) -> None:
        """Empties the plot down to the marks it keeps for whatever it draws next: the position
        indicator and the overlay rectangle, both of which live among the axis's children."""
        self._reconstruction_dimmed = False
        self._sample_rate = 0
        self._release_clock_ticks()
        self.clear_layers()
        dpg_delete_children(self.y_axis_tag)
        self.current_position = START_OF_AUDIO
        self._add_position_indicator()
        self._set_overlay_rectangle()

    def set_autoscale(self, autoscale: bool) -> None:
        self.reconstruction_autoscale = autoscale
        if isinstance(self.current_data, WaveformData):
            self.load_waveform_data(self.current_data)
            self._update_ranges()

    def _series_tag(self, layer_name: str) -> str:
        return compose_tag(self.y_axis_tag, layer_name)

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        self._prune_stale_series()
        for layer in self.layers.values():
            series_tag = self._series_tag(layer.name)
            self._upsert_series(series_tag, layer)
            self._bind_series_theme(series_tag, layer)

    def _series_shade(self, layer: Union[ArrayLayer, InstructionLayer]) -> SeriesShade:
        dimmed = self._reconstruction_dimmed and layer.name == self._lbl_waveform_reconstruction
        return SeriesShade.DIMMED if dimmed else SeriesShade.FULL

    def _series_color(
        self,
        layer: Union[ArrayLayer, InstructionLayer],
        shade: SeriesShade,
    ) -> BaseColor:
        """A layer's line color in one of its two shades.

        The dimmed reconstruction is desaturated to gray and faded, so the drawn waveform — not just
        the legend swatch — clearly reads as inactive while its audio is recomputed.
        """
        if shade is SeriesShade.DIMMED:
            reconstruction = self._layout.colors.waveform_reconstruction
            return FadedColor(
                color=GrayscaleColor(color=reconstruction),
                fraction=self._layout.waveform.reconstruction_dim_opacity,
            )

        return layer.color

    def _prune_stale_series(self) -> None:
        """Aligns the y-axis series with the current layers, keeping the position indicator
        and overlay rectangle attached across updates."""
        live_series_tags = {self._series_tag(layer_name) for layer_name in list(self.layers.keys())}
        preserved_tags = (self.position_indicator_tag, self.overlay_rectangle_tag)
        for child in dpg.get_item_children(self.y_axis_tag, 1) or []:
            child_tag = dpg.get_item_alias(child)
            if child_tag in preserved_tags:
                continue

            if child_tag not in live_series_tags:
                dpg_delete_item(child)

    def _upsert_series(
        self,
        series_tag: str,
        layer: Union[ArrayLayer, InstructionLayer],
    ) -> None:
        """Refreshes the points of an existing series, or creates it on the y-axis when new."""
        if dpg.does_item_exist(series_tag):
            dpg.configure_item(
                series_tag,
                x=layer.x_data,
                y=layer.y_data,
            )
        else:
            dpg.add_line_series(
                layer.x_data.tolist(),
                layer.y_data.tolist(),
                label=layer.name,
                parent=self.y_axis_tag,
                tag=series_tag,
            )

    def _bind_series_theme(
        self,
        series_tag: str,
        layer: Union[ArrayLayer, InstructionLayer],
    ) -> None:
        """Binds the theme drawing this layer in the shade it currently takes."""
        shade = self._series_shade(layer)
        dpg_bind_item_theme(series_tag, self._series_theme(self._series_color(layer, shade)))

    def _series_theme(self, color: BaseColor) -> str:
        """The theme drawing a line in one color, built once per color the graph has shown.

        A layer keeps its name across loads while its color follows what it draws — one
        generator's fragment after another's, the reconstruction line graying as its audio is
        recomputed — so the theme is held against the color rather than against the series that
        carries it, and a layer arriving in a new color binds the theme built for that color. Each
        theme holds the color token itself, so every color the graph has drawn follows a palette
        swap.

        Args:
            color: The color the line is drawn in.

        Returns:
            str: The tag of the theme carrying it.
        """
        if color in self._series_themes:
            return self._series_themes[color]

        theme_tag = compose_tag(self.tag, SUF_GRAPH_THEME, str(len(self._series_themes)))
        with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvLineSeries):
            dpg_add_palette_theme_color(
                dpg.mvPlotCol_Line,
                color,
                category=dpg.mvThemeCat_Plots,
            )

        self._series_themes[color] = theme_tag
        return theme_tag

    def _update_axes_limits(self) -> None:
        """Takes the new bounds, then names the positions they put on screen.

        The bounds are the graph's own, so the marks follow them the moment they are taken
        rather than waiting for a frame to state them back.
        """
        super()._update_axes_limits()
        self._restate_clock_ticks(*self.x_range)

    def _restate_zoomed_clock_ticks(self) -> None:
        """Names the positions across the stretch a reader has zoomed the plot to.

        A zoom moves the axis rather than the graph's own bounds, so the stretch is read back
        from the axis, a frame after the gesture that moved it has been drawn.
        """
        if not dpg.does_item_exist(self.x_axis_tag):
            return

        start, end = dpg.get_axis_limits(self.x_axis_tag)
        self._restate_clock_ticks(float(start), float(end))

    def _restate_clock_ticks(self, start: float, end: float) -> None:
        """Names each position along the time axis by the moment it stands at.

        The axis counts samples, so the stretch it covers turns into the seconds the recording
        reaches there and the marks are placed across them. A plot drawing a fragment counts
        samples alone, and the axis is handed back to the figures DearPyGui states for it.
        """
        if not dpg.does_item_exist(self.x_axis_tag):
            return

        named = (start, end, self._sample_rate)
        if named == self._named_span:
            return

        self._named_span = named
        ticks = self._clock_ticks(start, end)
        if ticks:
            dpg.set_axis_ticks(self.x_axis_tag, tuple(ticks))
        else:
            dpg.reset_axis_ticks(self.x_axis_tag)

    def _release_clock_ticks(self) -> None:
        """Hands the axis back to the figures DearPyGui states for it, which an empty plot reads by."""
        self._named_span = None
        if dpg.does_item_exist(self.x_axis_tag):
            dpg.reset_axis_ticks(self.x_axis_tag)

    def _clock_ticks(self, start: float, end: float) -> List[ClockTick]:
        """The marks the stretch between two sample positions carries, which a recording names."""
        if self._sample_rate <= 0:
            return []

        return clock_ticks(
            seconds_from_samples(int(start), self._sample_rate),
            seconds_from_samples(int(end), self._sample_rate),
            self._sample_rate,
            self._layout.clock,
        )

    def _add_position_indicator(self) -> None:
        dpg_delete_item(self.position_indicator_tag)
        dpg.add_inf_line_series(
            [0.0],
            tag=self.position_indicator_tag,
            parent=self.y_axis_tag,
            show=False,
        )
        self.indicator_theme.bind_to_item(self.position_indicator_tag)

    def _update_position_indicator(self) -> None:
        position_x = float(self.current_position)
        show = position_x > 0
        dpg_configure_item(
            self.position_indicator_tag,
            x=[position_x],
            show=show,
        )

    def set_position(self, position: int) -> None:
        self.current_position = position
        self._update_position_indicator()
