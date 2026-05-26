from sampletones_shared.utils.callbacks import CallbackMixin

from ....config.manager import ConfigManager


class SequencerGridLogic(CallbackMixin):
    def __init__(self, config_manager: ConfigManager) -> None:
        self._config_manager = config_manager

    @property
    def change_rate(self) -> int:
        return self._config_manager.config.library.change_rate
