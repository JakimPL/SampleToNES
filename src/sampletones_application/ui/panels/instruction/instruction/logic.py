from typing import Optional

from sampletones_core.configs import InstructionsLibraryConfig


class InstructionPanelLogic:
    def __init__(self) -> None:
        self._library_config: Optional[InstructionsLibraryConfig] = None

    def update_config(self, config: Optional[InstructionsLibraryConfig]) -> None:
        self._library_config = config

    def is_loaded(self) -> bool:
        return self._library_config is not None
