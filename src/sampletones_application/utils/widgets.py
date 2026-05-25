from typing import Union

import dearpygui.dearpygui as dpg

from sampletones_shared.utils.arrays import clamp


def clamp_widget_value(tag: str) -> Union[int, float, bool, str]:
    value: Union[int, float, bool, str] = dpg.get_value(tag)
    item_config = dpg.get_item_configuration(tag)

    min_v = item_config.get("min_value")
    max_v = item_config.get("max_value")

    if isinstance(value, (int, float)):
        value = clamp(value, min_v, max_v)

    return value
