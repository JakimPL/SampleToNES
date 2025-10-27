from typing import Optional

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
from browser.waveform.layer import WaveformLayer
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
        dpg.add_text("No spectrum loaded", tag=self.info_tag)
        with dpg.plot(
            label=self.label,
            height=self.height,
            width=self.width,
            tag=self.plot_tag,
            anti_aliased=True,
            no_inputs=True,
        ):
            dpg.add_plot_legend(tag=self.legend_tag)
            dpg.add_plot_axis(dpg.mvXAxis, label=LBL_SPECTRUM_X_AXIS, tag=self.x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, label=LBL_SPECTRUM_Y_AXIS, tag=self.y_axis_tag)

    def load_library_fragment(self, fragment: LibraryFragment, sample_rate: int) -> None:
        self.current_library_fragment = fragment
        self.spectrum = fragment.feature
        fragment_length = len(self.spectrum)
        self.frequencies = calculate_frequencies(fragment_length, sample_rate)
        self._update_display()
        self._update_info_display()

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        children = dpg.get_item_children(self.y_axis_tag, slot=VAL_WAVEFORM_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

        if self.spectrum is None or self.frequencies is None:
            return

        norm = float(np.max(self.spectrum)) if np.max(self.spectrum) > 0 else 1.0
        energies = self.spectrum / norm

        log_freqs = np.log10(self.frequencies + VAL_SPECTRUM_LOG_OFFSET)
        min_log = float(np.min(log_freqs))
        max_log = float(np.max(log_freqs))

        x_data = log_freqs.tolist()
        y_data = energies.tolist()

        series_tag = f"{self.y_axis_tag}_spectrum"
        dpg.add_bar_series(x_data, y_data, label="Spectrum", parent=self.y_axis_tag, tag=series_tag)

        # DearPyGui does not support per-bar or bar series color theming for bar series in any version.
        # The bars will use the default color set by the DearPyGui style/theme.

        dpg.set_axis_limits(self.x_axis_tag, min_log, max_log)
        dpg.set_axis_limits(self.y_axis_tag, 0.0, 1.0)

    def _update_info_display(self) -> None:
        if not dpg.does_item_exist(self.info_tag):
            return
        if not self.current_library_fragment:
            dpg.set_value(self.info_tag, "No spectrum loaded")
            return
        dpg.set_value(self.info_tag, "")
