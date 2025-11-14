from typing import Any, Callable, Dict, Optional

import dearpygui.dearpygui as dpg

from ..constants import SUF_BUTTON


class GUIButton:
    REGISTRY: Dict[str, "GUIButton"] = {}

    def __init__(
        self,
        tag: str,
        label: str,
        callback: Callable[..., Any],
        enabled: bool = True,
        **kwargs,
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
        enabled = dpg.is_item_enabled(self._tag)
        assert enabled is not None
        return enabled

    def configure_item(self, **kwargs) -> None:
        dpg.configure_item(self._button_tag, **kwargs)
        if "enabled" in kwargs:
            self.set_enabled(kwargs["enabled"])

    def get_item_label(self) -> Optional[str]:
        return dpg.get_item_label(self._button_tag)

    def set_item_label(self, label: str) -> None:
        return dpg.set_item_label(self._button_tag, label)

    def set_item_callback(self, callback: Callable) -> None:
        return dpg.set_item_callback(self._button_tag, callback)

    def set_value(self, value: Any) -> None:
        return dpg.set_value(self._button_tag, value)

    def delete_item(self) -> None:
        dpg.delete_item(self._button_tag)
        dpg.delete_item(self._tag)
        if self._tag in GUIButton.REGISTRY:
            del GUIButton.REGISTRY[self._tag]

    @property
    def tag(self) -> str:
        return self._tag
