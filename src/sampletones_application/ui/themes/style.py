from dataclasses import dataclass
from typing import Union

import dearpygui.dearpygui as dpg

from sampletones_application.utils.palette.colors.base import BaseColor


@dataclass(frozen=True, kw_only=True)
class ThemeValue:
    key: int
    category: int = dpg.mvThemeCat_Core


@dataclass(frozen=True, kw_only=True)
class ThemeColor(ThemeValue):
    color: BaseColor


@dataclass(frozen=True, kw_only=True)
class ThemeStyle(ThemeValue):
    x: Union[int, float]
    y: Union[int, float] = -1.0


@dataclass(frozen=True)
class ThemeParameter:
    item_type: int
    enabled_state: bool = True
