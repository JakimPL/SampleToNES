from sampletones_application.config.manager import ConfigManager
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerGridLogic(CallbackMixin):
    def __init__(self, config_manager: ConfigManager) -> None:
        self._config_manager = config_manager

    @property
    def change_rate(self) -> int:
        return self._config_manager.config.library.change_rate
