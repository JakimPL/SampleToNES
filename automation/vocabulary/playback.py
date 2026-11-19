from typing import Dict, Final

from sampletones_core.constants.enums import AudioSourceType

PAUSE: Final[str] = "global.menu.label.item_playback_pause"
PLAY: Final[str] = "global.menu.label.item_playback_play"
PLAY_VOICE: Final[str] = "global.context.label.play"
RESUME: Final[str] = "global.menu.label.item_playback_resume"
ORIGINAL_SWITCH: Final[str] = "reconstructions.reconstruction.label.original_audio_radio"
RECONSTRUCTION_SWITCH: Final[str] = "reconstructions.reconstruction.label.reconstruction_radio"
SOURCE_SWITCHES: Final[Dict[AudioSourceType, str]] = {
    AudioSourceType.ORIGINAL: ORIGINAL_SWITCH,
    AudioSourceType.RECONSTRUCTION: RECONSTRUCTION_SWITCH,
}
