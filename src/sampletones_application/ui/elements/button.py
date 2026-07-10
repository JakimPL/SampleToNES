from __future__ import annotations

from typing import Any, Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import SUF_BUTTON, TAG_GLOBAL_THEME_DEFAULT
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback


class GUIButton:
    _REGISTRY: Dict[Sender, GUIButton] = {}

    def __init__(
        self,
        tag: str,
        label: str,
        parent: Optional[str] = None,
        callback: Optional[Callback] = None,
        enabled: bool = True,
        font: Font = Font.REGULAR,
        theme: Optional[Theme] = None,
        **kwargs: Any,
    ) -> None:
        self._tag = tag
        self._parent = parent
        self._button_tag = f"{tag}{SUF_BUTTON}"
        callback = callback if callback is not None else lambda: None
        resolved_theme = ThemeRegistry.resolve(theme, TAG_GLOBAL_THEME_DEFAULT)

        group_kwargs = {
            "tag": tag,
            "horizontal": True,
            "enabled": enabled,
        }

        if parent is not None:
            group_kwargs["parent"] = parent

        with dpg.group(**group_kwargs):
            dpg.add_button(
                label=label,
                tag=self._button_tag,
                parent=tag,
                callback=callback,
                enabled=enabled,
                **kwargs,
            )

            resolved_theme.bind_to_item(self._tag)
            resolved_theme.bind_to_item(self._button_tag)
            FontRegistry.bind_to_item(self._button_tag, font)

        GUIButton._REGISTRY[tag] = self

    @classmethod
    def exists(cls, tag: Sender) -> bool:
        tag = dpg.get_item_alias(tag)
        return tag in cls._REGISTRY

    @classmethod
    def get(cls, tag: Sender) -> Optional[GUIButton]:
        tag = dpg.get_item_alias(tag)
        return cls._REGISTRY.get(tag)

    @classmethod
    def delete(cls, tag: Sender) -> None:
        tag = dpg.get_item_alias(tag)
        if tag in cls._REGISTRY:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            del cls._REGISTRY[tag]

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

    def set_item_callback(self, callback: Callback) -> None:
        dpg.set_item_callback(self._button_tag, callback)

    def set_theme(self, theme: Theme) -> None:
        theme.bind_to_item(self._tag)
        theme.bind_to_item(self._button_tag)

    def get_value(self) -> Any:
        return dpg.get_value(self._button_tag)

    def set_value(self, value: Any) -> None:
        dpg.set_value(self._button_tag, value)

    def delete_item(self) -> None:
        dpg.delete_item(self._button_tag)
        dpg.delete_item(self._tag)
        if self._tag in GUIButton._REGISTRY:
            del GUIButton._REGISTRY[self._tag]

    def is_item_hovered(self) -> Optional[bool]:
        is_hovered: Optional[bool] = dpg.is_item_hovered(self._button_tag)
        return is_hovered

    @property
    def tag(self) -> str:
        return self._tag
