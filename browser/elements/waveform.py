from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg
import numpy as np

from browser.constants import (
    BUTTON_PLAY_AUDIO,
    BUTTON_RESET_ALL,
    BUTTON_RESET_X,
    BUTTON_RESET_Y,
    WAVEFORM_AMPLITUDE_LABEL,
    WAVEFORM_AXIS_SLOT,
    WAVEFORM_DEFAULT_Y_MAX,
    WAVEFORM_DEFAULT_Y_MIN,
    WAVEFORM_FEATURE_COLOR,
    WAVEFORM_FEATURE_NAME_FORMAT,
    WAVEFORM_FEATURE_SCALE,
    WAVEFORM_FREQUENCY_FORMAT,
    WAVEFORM_FREQUENCY_PREFIX,
    WAVEFORM_GENERATOR_PREFIX,
    WAVEFORM_HOVER_PREFIX,
    WAVEFORM_NO_FRAGMENT_MSG,
    WAVEFORM_OFFSET_PREFIX,
    WAVEFORM_PARAMETERS_HEADER,
    WAVEFORM_POSITION_FORMAT,
    WAVEFORM_RECONSTRUCTION_COLOR,
    WAVEFORM_RECONSTRUCTION_LAYER_NAME,
    WAVEFORM_RECONSTRUCTION_THICKNESS,
    WAVEFORM_SAMPLE_COLOR,
    WAVEFORM_SAMPLE_LAYER_NAME,
    WAVEFORM_SAMPLE_LENGTH_PREFIX,
    WAVEFORM_SAMPLE_THICKNESS,
    WAVEFORM_TIME_LABEL,
    WAVEFORM_VALUE_FORMAT,
    WAVEFORM_ZOOM_FACTOR,
)
from library.data import LibraryFragment
from typehints.instructions import InstructionUnion
from utils.audioio import play_audio


@dataclass
class WaveformLayer:
    name: str
    data: np.ndarray
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    visible: bool = True
    line_thickness: float = 1.0


class Waveform:
    def __init__(
        self,
        tag: str,
        width: int = -1,
        height: int = 300,
        parent: Optional[str] = None,
        label: str = "Waveform Display",
    ):
        self.tag = tag
        self.width = width
        self.height = height
        self.parent = parent
        self.label = label

        self.plot_tag = f"{tag}_plot"
        self.x_axis_tag = f"{tag}_x_axis"
        self.y_axis_tag = f"{tag}_y_axis"
        self.legend_tag = f"{tag}_legend"
        self.controls_tag = f"{tag}_controls"
        self.info_tag = f"{tag}_info"

        self.layers: Dict[str, WaveformLayer] = {}
        self.current_library_fragment: Optional[LibraryFragment] = None

        self.x_min: float = 0.0
        self.x_max: float = 1.0
        self.y_min: float = WAVEFORM_DEFAULT_Y_MIN
        self.y_max: float = WAVEFORM_DEFAULT_Y_MAX
        self.default_y_range = (WAVEFORM_DEFAULT_Y_MIN, WAVEFORM_DEFAULT_Y_MAX)

        self.is_dragging = False
        self.last_mouse_pos: Optional[List[float]] = None
        self.zoom_factor = WAVEFORM_ZOOM_FACTOR

        self._create_display()

    def _create_display(self) -> None:
        if self.parent:
            dpg.group(tag=self.tag, parent=self.parent)
        else:
            dpg.group(tag=self.tag)
            with dpg.group(tag=self.controls_tag, horizontal=True):
                dpg.add_button(label=BUTTON_RESET_X, callback=self._reset_x_axis, small=True)
                dpg.add_button(label=BUTTON_RESET_Y, callback=self._reset_y_axis, small=True)
                dpg.add_button(label=BUTTON_RESET_ALL, callback=self._reset_all_axes, small=True)
                dpg.add_button(label=BUTTON_PLAY_AUDIO, callback=self._play_current_audio, small=True)

            with dpg.group(tag=f"{self.controls_tag}_layers", horizontal=True):
                pass

            dpg.add_text(WAVEFORM_NO_FRAGMENT_MSG, tag=self.info_tag)

            with dpg.plot(
                label=self.label,
                height=self.height,
                width=self.width,
                tag=self.plot_tag,
                callback=self._plot_callback,
                anti_aliased=True,
            ):
                dpg.add_plot_legend(tag=self.legend_tag)
                dpg.add_plot_axis(dpg.mvXAxis, label=WAVEFORM_TIME_LABEL, tag=self.x_axis_tag)
                dpg.add_plot_axis(dpg.mvYAxis, label=WAVEFORM_AMPLITUDE_LABEL, tag=self.y_axis_tag)

            with dpg.handler_registry():
                dpg.add_mouse_wheel_handler(callback=self._mouse_wheel_callback)
                dpg.add_mouse_drag_handler(callback=self._mouse_drag_callback)
                dpg.add_mouse_move_handler(callback=self._mouse_move_callback)

    def add_layer(
        self,
        name: str,
        data: np.ndarray,
        color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        visible: bool = True,
        line_thickness: float = 1.0,
    ) -> None:
        layer = WaveformLayer(name, data, color, visible, line_thickness)
        self.layers[name] = layer
        self._update_display()

    def remove_layer(self, name: str) -> None:
        if name in self.layers:
            del self.layers[name]
            self._update_display()

    def set_layer_visibility(self, name: str, visible: bool) -> None:
        if name in self.layers:
            self.layers[name].visible = visible
            self._update_display()

    def clear_layers(self) -> None:
        self.layers.clear()
        self._update_display()

    def load_library_fragment(self, fragment: LibraryFragment) -> None:
        self.current_library_fragment = fragment
        self.clear_layers()

        self.add_layer(
            WAVEFORM_SAMPLE_LAYER_NAME,
            fragment.sample,
            color=WAVEFORM_SAMPLE_COLOR,
            line_thickness=WAVEFORM_SAMPLE_THICKNESS,
        )

        if len(fragment.feature) > 0:
            feature_scaled = fragment.feature * WAVEFORM_FEATURE_SCALE
            self.add_layer(
                WAVEFORM_FEATURE_NAME_FORMAT.format(fragment.frequency),
                feature_scaled,
                color=WAVEFORM_FEATURE_COLOR,
                visible=False,
            )

        self._update_info_display()
        self._update_layer_controls()

        self.x_min = 0.0
        self.x_max = float(len(fragment.sample))
        self._update_axes_limits()

    def add_reconstruction_comparison(self, reconstruction: np.ndarray) -> None:
        if len(reconstruction) > 0:
            self.add_layer(
                WAVEFORM_RECONSTRUCTION_LAYER_NAME,
                reconstruction,
                color=WAVEFORM_RECONSTRUCTION_COLOR,
                line_thickness=WAVEFORM_RECONSTRUCTION_THICKNESS,
            )

    def _update_display(self) -> None:
        children = dpg.get_item_children(self.y_axis_tag, slot=WAVEFORM_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

        for layer in self.layers.values():
            if layer.visible and len(layer.data) > 0:
                x_data = [float(i) for i in range(len(layer.data))]
                y_data = layer.data.tolist()

                dpg.add_line_series(x_data, y_data, label=layer.name, parent=self.y_axis_tag, color=layer.color)

        self._update_axes_limits()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)

    def _update_layer_controls(self) -> None:
        layers_control_tag = f"{self.controls_tag}_layers"

        children = dpg.get_item_children(layers_control_tag, slot=WAVEFORM_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

        for layer_name, layer in self.layers.items():
            button_tag = f"{layers_control_tag}_{layer_name.replace(' ', '_')}"
            dpg.add_checkbox(
                label=layer_name,
                default_value=layer.visible,
                callback=lambda sender, app_data, user_data=layer_name: self.set_layer_visibility(user_data, app_data),
                parent=layers_control_tag,
                tag=button_tag,
            )

    def _update_info_display(self) -> None:
        if not self.current_library_fragment:
            dpg.set_value(self.info_tag, WAVEFORM_NO_FRAGMENT_MSG)
            return

        fragment = self.current_library_fragment
        info_text = self._format_instruction_info(fragment.instruction, fragment)
        dpg.set_value(self.info_tag, info_text)

    def _format_instruction_info(self, instruction: InstructionUnion, fragment: LibraryFragment) -> str:
        info_lines = [
            f"{WAVEFORM_GENERATOR_PREFIX}{fragment.generator_class.capitalize()}",
            f"{WAVEFORM_FREQUENCY_PREFIX}{WAVEFORM_FREQUENCY_FORMAT.format(fragment.frequency)}",
            f"{WAVEFORM_SAMPLE_LENGTH_PREFIX}{len(fragment.sample)} samples",
            f"{WAVEFORM_OFFSET_PREFIX}{fragment.offset}",
            "",
            WAVEFORM_PARAMETERS_HEADER,
        ]

        for field_name, field_value in instruction.model_dump().items():
            if field_name == "name":
                continue
            formatted_value = self._format_parameter_value(field_value)
            info_lines.append(f"  {field_name}: {formatted_value}")

        return "\n".join(info_lines)

    def _format_parameter_value(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.4f}"
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, (list, tuple)):
            return f"[{', '.join(str(v) for v in value)}]"
        else:
            return str(value)

    def _reset_x_axis(self) -> None:
        if self.layers:
            max_length = max(len(layer.data) for layer in self.layers.values())
            self.x_min = 0.0
            self.x_max = float(max_length)
        else:
            self.x_min = 0.0
            self.x_max = 1.0
        self._update_axes_limits()

    def _reset_y_axis(self) -> None:
        self.y_min, self.y_max = self.default_y_range
        self._update_axes_limits()

    def _reset_all_axes(self) -> None:
        self._reset_x_axis()
        self._reset_y_axis()

    def _play_current_audio(self) -> None:
        if self.current_library_fragment:
            play_audio(self.current_library_fragment.sample)

    def _plot_callback(self, sender: str, app_data: Any) -> None:
        pass

    def _mouse_wheel_callback(self, sender: str, app_data: float) -> None:
        if dpg.is_item_hovered(self.plot_tag):
            plot_mouse_pos = dpg.get_plot_mouse_pos()
            if plot_mouse_pos[0] and plot_mouse_pos[1]:
                zoom_amount = self.zoom_factor if app_data > 0 else 1.0 / self.zoom_factor

                center_x = plot_mouse_pos[0]
                center_y = plot_mouse_pos[1]

                x_range = self.x_max - self.x_min
                y_range = self.y_max - self.y_min

                new_x_range = x_range / zoom_amount
                new_y_range = y_range / zoom_amount

                x_offset = (center_x - self.x_min) / x_range
                y_offset = (center_y - self.y_min) / y_range

                self.x_min = center_x - new_x_range * x_offset
                self.x_max = center_x + new_x_range * (1.0 - x_offset)
                self.y_min = center_y - new_y_range * y_offset
                self.y_max = center_y + new_y_range * (1.0 - y_offset)

                self._update_axes_limits()

    def _mouse_drag_callback(self, sender: str, app_data: Tuple[float, float]) -> None:
        if dpg.is_item_hovered(self.plot_tag) and dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            if not self.is_dragging:
                self.is_dragging = True
                mouse_pos = dpg.get_plot_mouse_pos()
                self.last_mouse_pos = [float(mouse_pos[0]), float(mouse_pos[1])] if mouse_pos[0] else None
                return

            current_pos = dpg.get_plot_mouse_pos()
            if current_pos[0] and current_pos[1] and self.last_mouse_pos:
                dx = float(current_pos[0]) - self.last_mouse_pos[0]
                dy = float(current_pos[1]) - self.last_mouse_pos[1]

                self.x_min -= dx
                self.x_max -= dx
                self.y_min -= dy
                self.y_max -= dy

                self._update_axes_limits()
                self.last_mouse_pos = [float(current_pos[0]), float(current_pos[1])]
        else:
            self.is_dragging = False

    def _mouse_move_callback(self, sender: str, app_data: Tuple[float, float]) -> None:
        if dpg.is_item_hovered(self.plot_tag):
            mouse_pos = dpg.get_plot_mouse_pos()
            if mouse_pos[0] and mouse_pos[1]:
                hover_info = WAVEFORM_POSITION_FORMAT.format(mouse_pos[0], mouse_pos[1])

                closest_info = self._get_closest_point_info(mouse_pos[0], mouse_pos[1])
                if closest_info:
                    hover_info += f" | {closest_info}"

                if self.current_library_fragment:
                    original_info = self._format_instruction_info(
                        self.current_library_fragment.instruction, self.current_library_fragment
                    )
                    dpg.set_value(self.info_tag, f"{original_info}\n\n{WAVEFORM_HOVER_PREFIX}{hover_info}")
                else:
                    dpg.set_value(self.info_tag, f"{WAVEFORM_HOVER_PREFIX}{hover_info}")

    def _get_closest_point_info(self, x: float, y: float) -> Optional[str]:
        closest_layer = None
        closest_distance = float("inf")
        closest_index = 0
        closest_value = 0.0

        sample_x = int(round(x))

        for layer_name, layer in self.layers.items():
            if layer.visible and 0 <= sample_x < len(layer.data):
                sample_value = layer.data[sample_x]
                distance = abs(sample_value - y)

                if distance < closest_distance:
                    closest_distance = distance
                    closest_layer = layer_name
                    closest_index = sample_x
                    closest_value = sample_value

        return WAVEFORM_VALUE_FORMAT.format(closest_layer, closest_index, closest_value) if closest_layer else None

    def set_view_bounds(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self._update_axes_limits()

    def get_view_bounds(self) -> Tuple[float, float, float, float]:
        return self.x_min, self.x_max, self.y_min, self.y_max

    def export_view_as_image(self, path: Union[str, Path]) -> None:
        pass
