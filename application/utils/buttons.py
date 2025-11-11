from typing import Any, Callable, Dict

import dearpygui.dearpygui as dpg

from constants.browser import SUF_BUTTON


class GUIButton:
    _REGISTRY: Dict[str, "GUIButton"] = {}

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

        GUIButton._REGISTRY[tag] = self

    def set_enabled(self, enabled: bool) -> None:
        dpg.configure_item(self._tag, enabled=enabled)

    def is_enabled(self) -> bool:
        enabled = dpg.is_item_enabled(self._tag)
        assert enabled is not None
        return enabled

    def configure(self, **kwargs) -> None:
        dpg.configure_item(self._button_tag, **kwargs)
        if "enabled" in kwargs:
            self.set_enabled(kwargs["enabled"])

    @classmethod
    def configure_item(cls, tag: str, **kwargs) -> None:
        if tag in cls._REGISTRY:
            cls._REGISTRY[tag].configure(**kwargs)
        else:
            dpg.configure_item(tag, **kwargs)

    @property
    def tag(self) -> str:
        return self._tag
