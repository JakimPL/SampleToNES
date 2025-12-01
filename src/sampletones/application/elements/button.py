from typing import Any, Callable, Dict, Optional

import dearpygui.dearpygui as dpg

from ..constants import (
    COL_BUTTON_SPECIAL,
    COL_BUTTON_SPECIAL_ACTIVE,
    COL_BUTTON_SPECIAL_HOVERED,
    SUF_BUTTON,
    TAG_FONT_BOLD,
    TAG_THEME_BUTTON,
    VAL_BUTTON_SPECIAL_FRAME_PADDING,
    VAL_BUTTON_SPECIAL_FRAME_ROUNDING,
)


def create_button_theme() -> str:
    if dpg.does_item_exist(TAG_THEME_BUTTON):
        return TAG_THEME_BUTTON

    with dpg.theme(tag=TAG_THEME_BUTTON):
        with dpg.theme_component():
            dpg.add_theme_color(dpg.mvThemeCol_Button, COL_BUTTON_SPECIAL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COL_BUTTON_SPECIAL_HOVERED, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, COL_BUTTON_SPECIAL_ACTIVE, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(
                dpg.mvStyleVar_FrameRounding,
                VAL_BUTTON_SPECIAL_FRAME_ROUNDING,
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_FramePadding,
                *VAL_BUTTON_SPECIAL_FRAME_PADDING,
                category=dpg.mvThemeCat_Core,
            )
    return TAG_THEME_BUTTON


class GUIButton:
    REGISTRY: Dict[str, "GUIButton"] = {}

    def __init__(
        self,
        tag: str,
        label: str,
        callback: Callable[..., Any],
        enabled: bool = True,
        **kwargs: Any,
    ) -> None:
        self._tag = tag
        self._button_tag = f"{tag}{SUF_BUTTON}"
        with dpg.group(tag=tag, horizontal=True, enabled=enabled):
            dpg.add_button(
                label=label,
                tag=self._button_tag,
                callback=callback,
                enabled=enabled,
                **kwargs,
            )

            dpg.bind_item_theme(self._button_tag, create_button_theme())
            dpg.bind_item_font(self._button_tag, TAG_FONT_BOLD)
        GUIButton.REGISTRY[tag] = self

    @classmethod
    def delete(cls, tag: str) -> None:
        if tag in cls.REGISTRY:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            del cls.REGISTRY[tag]

    def set_enabled(self, enabled: bool) -> None:
        dpg.configure_item(self._tag, enabled=enabled)

    def is_enabled(self) -> bool:
        enabled: Optional[bool] = dpg.is_item_enabled(self._tag)
        assert enabled is not None
        return enabled

    def configure_item(self, **kwargs: Any) -> None:
        dpg.configure_item(self._button_tag, **kwargs)
        if "enabled" in kwargs:
            self.set_enabled(kwargs["enabled"])

    def get_item_label(self) -> Optional[str]:
        label: Optional[str] = dpg.get_item_label(self._button_tag)
        return label

    def set_item_label(self, label: str) -> None:
        dpg.set_item_label(self._button_tag, label)

    def set_item_callback(self, callback: Callable[..., Any]) -> None:
        dpg.set_item_callback(self._button_tag, callback)

    def set_value(self, value: Any) -> None:
        dpg.set_value(self._button_tag, value)

    def delete_item(self) -> None:
        dpg.delete_item(self._button_tag)
        dpg.delete_item(self._tag)
        if self._tag in GUIButton.REGISTRY:
            del GUIButton.REGISTRY[self._tag]

    @property
    def tag(self) -> str:
        return self._tag
