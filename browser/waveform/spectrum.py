from typing import Optional, Tuple

import dearpygui.dearpygui as dpg
import numpy as np

from browser.constants import (
    DIM_WAVEFORM_DEFAULT_DISPLAY_HEIGHT,
    DIM_WAVEFORM_DEFAULT_WIDTH,
    LBL_SPECTRUM_X_AXIS,
    LBL_SPECTRUM_Y_AXIS,
    SUF_WAVEFORM_INFO,
    SUF_WAVEFORM_LEGEND,
    SUF_WAVEFORM_PLOT,
    SUF_WAVEFORM_X_AXIS,
    SUF_WAVEFORM_Y_AXIS,
    VAL_SPECTRUM_GRAYSCALE_MAX,
    VAL_SPECTRUM_LOG_OFFSET,
    VAL_WAVEFORM_AXIS_SLOT,
)
from constants import MIN_FREQUENCY, SAMPLE_RATE
from ffts.fft import calculate_frequencies
from library.data import LibraryFragment


class SpectrumDisplay:
    def __init__(
        self,
        tag: str,
        width: int = DIM_WAVEFORM_DEFAULT_WIDTH,
        height: int = DIM_WAVEFORM_DEFAULT_DISPLAY_HEIGHT,
        parent: Optional[str] = None,
        label: str = "Spectrum Display",
    ) -> None:
        self.tag = tag
        self.width = width
        self.height = height
        self.parent = parent
        self.label = label

        self.plot_tag = f"{tag}{SUF_WAVEFORM_PLOT}"
        self.x_axis_tag = f"{tag}{SUF_WAVEFORM_X_AXIS}"
        self.y_axis_tag = f"{tag}{SUF_WAVEFORM_Y_AXIS}"
        self.legend_tag = f"{tag}{SUF_WAVEFORM_LEGEND}"
        self.info_tag = f"{tag}{SUF_WAVEFORM_INFO}"

        self.current_library_fragment: Optional[LibraryFragment] = None
        self.spectrum: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None

        self._create_display()

    def _create_display(self) -> None:
        if self.parent:
            with dpg.group(tag=self.tag, parent=self.parent):
                self._create_spectrum_content()
        else:
            with dpg.group(tag=self.tag):
                self._create_spectrum_content()

    def _create_spectrum_content(self) -> None:
        with dpg.plot(
            label=self.label,
            height=self.height,
            width=self.width,
            tag=self.plot_tag,
            anti_aliased=True,
            no_inputs=True,
            pan_button=-1,
        ):
            dpg.add_plot_axis(dpg.mvXAxis, label=LBL_SPECTRUM_X_AXIS, tag=self.x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, label=LBL_SPECTRUM_Y_AXIS, tag=self.y_axis_tag, scale=dpg.mvPlotScale_Log10)
            dpg.set_axis_limits(self.y_axis_tag, MIN_FREQUENCY, SAMPLE_RATE // 2)

    def load_library_fragment(
        self,
        fragment: LibraryFragment,
        sample_rate: int,
        frame_length: int,
    ) -> None:
        self.current_library_fragment = fragment
        self.spectrum = fragment.feature
        self.frequencies = calculate_frequencies(frame_length, sample_rate)
        self._update_display()

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        children = dpg.get_item_children(self.y_axis_tag, slot=VAL_WAVEFORM_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

        if self.spectrum is None or self.frequencies is None:
            return

        total_energy = np.sqrt(np.sum(self.spectrum**2)) + VAL_SPECTRUM_LOG_OFFSET
        normalized_spectrum: np.ndarray = self.spectrum / total_energy
        frequencies: np.ndarray = self.frequencies
        for bin_index, (frequency, energy) in enumerate(zip(frequencies, normalized_spectrum)):
            frequency_lower_bound, frequency_upper_bound = self._get_frequency_band_bounds(frequencies, bin_index)
            frequency_band_width = frequency_upper_bound - frequency_lower_bound
            series_tag = f"{self.y_axis_tag}_bar_{bin_index}"
            dpg.add_bar_series(
                x=[1.0],
                y=[frequency],
                label="",
                parent=self.y_axis_tag,
                tag=series_tag,
                weight=frequency_band_width,
                horizontal=True,
            )
            with dpg.theme() as bar_theme:
                with dpg.theme_component(dpg.mvBarSeries):
                    brightness = int(VAL_SPECTRUM_GRAYSCALE_MAX * energy)
                    dpg.add_theme_color(
                        dpg.mvPlotCol_Fill,
                        (
                            VAL_SPECTRUM_GRAYSCALE_MAX,
                            VAL_SPECTRUM_GRAYSCALE_MAX,
                            VAL_SPECTRUM_GRAYSCALE_MAX,
                            brightness,
                        ),
                        category=dpg.mvThemeCat_Plots,
                    )
            dpg.bind_item_theme(series_tag, bar_theme)

        self._update_axis_limits()

    def _update_axis_limits(self) -> None:
        if self.frequencies is None:
            return

        dpg.set_axis_limits(self.y_axis_tag, self.frequencies[0], self.frequencies[-1])

    def _get_frequency_band_bounds(self, frequencies: np.ndarray, bin_index: int) -> Tuple[float, float]:
        bin_count: int = len(frequencies)
        frequency: float = frequencies[bin_index]

        if bin_index == 0:
            frequency_lower_bound = np.sqrt(frequencies[0] * frequencies[1])
        else:
            frequency_lower_bound = np.sqrt(frequencies[bin_index - 1] * frequency)
        if bin_index == bin_count - 1:
            frequency_upper_bound = np.sqrt(frequencies[-1] ** 2 / frequencies[-2])
        else:
            frequency_upper_bound = np.sqrt(frequency * frequencies[bin_index + 1])

        return frequency_lower_bound, frequency_upper_bound
