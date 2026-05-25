from abc import ABC, abstractmethod
from typing import Any, Union

import dearpygui.dearpygui as dpg

from sampletones_shared.types.application import Sender

from ..config.application.manager import ApplicationConfigManager
from ..config.manager import ConfigManager
from ..constants.general import SUF_HANDLER_REGISTRY
from .panel import GUIPanel


class GUISettingsPanel(GUIPanel, ABC):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        tag: str,
        parent: str,
        width: int = 0,
        height: int = 0,
        init: bool = False,
    ):
        self.config_manager = config_manager
        self.application_config_manager = application_config_manager

        self._item_handler_tag = f"{tag}{SUF_HANDLER_REGISTRY}"

        super().__init__(
            tag=tag,
            parent=parent,
            width=width,
            height=height,
            init=init,
        )

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    @abstractmethod
    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None: ...

    def _clamp_value(self, tag: str) -> Union[int, float, bool, str]:
        value: Union[int, float, bool, str] = dpg.get_value(tag)
        item_config = dpg.get_item_configuration(tag)

        min_v = item_config.get("min_value")
        max_v = item_config.get("max_value")

        if isinstance(value, (int, float)):
            if min_v is not None:
                value = max(value, min_v)
            if max_v is not None:
                value = min(value, max_v)

        return value

    @abstractmethod
    def update_gui_from_config(self) -> None: ...
