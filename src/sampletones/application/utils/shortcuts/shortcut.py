from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from .keys import KEY_DISPLAY_NAMES, Modifier


@dataclass(frozen=True)
class Shortcut:
    key: int
    modifiers: Tuple[Modifier, ...] = ()

    def get_display_string(self) -> str:
        parts = [modifier.value for modifier in self.modifiers]
        parts.append(self._key_to_string())
        return "+".join(parts)

    def _key_to_string(self) -> str:
        return KEY_DISPLAY_NAMES.get(self.key, "?")


class ShortcutId(Enum):
    SAVE_CONFIGURATION = "SaveConfiguration"
    LOAD_CONFIGURATION = "LoadConfiguration"
    AUDIO_SETTINGS = "AudioSettings"
    EXIT = "Exit"
    CLOSE_RECONSTRUCTION = "CloseReconstruction"
    LOAD_RECONSTRUCTION = "LoadReconstruction"
    RECONSTRUCT_FILE = "ReconstructFile"
    RECONSTRUCT_DIRECTORY = "ReconstructDirectory"
    EXPORT_RECONSTRUCTION_WAV = "ExportReconstructionWav"
    EXPORT_RECONSTRUCTION_FTIS = "ExportReconstructionFTIs"
    FULLSCREEN_TOGGLE = "FullscreenToggle"
    ABOUT_DIALOG = "AboutDialog"
    PLAY = "Play"
    STOP = "Stop"
    PAUSE = "Pause"
