from enum import Enum


class ShortcutId(Enum):
    SAVE_CONFIGURATION = "SaveConfiguration"
    LOAD_CONFIGURATION = "LoadConfiguration"
    AUDIO_SETTINGS = "AudioSettings"
    EXIT = "Exit"
    SAVE_RECONSTRUCTION = "SaveReconstruction"
    SAVE_RECONSTRUCTION_AS = "SaveReconstructionAs"
    LOAD_RECONSTRUCTION = "LoadReconstruction"
    CLOSE_RECONSTRUCTION = "CloseReconstruction"
    RECONSTRUCT_FILE = "ReconstructFile"
    RECONSTRUCT_DIRECTORY = "ReconstructDirectory"
    EXPORT_RECONSTRUCTION_WAV = "ExportReconstructionWav"
    EXPORT_RECONSTRUCTION_FTIS = "ExportReconstructionFTIs"
    PLAY_FROM_START = "PlayFromStart"
    STOP = "Stop"
    PLAY = "Play"
    TOGGLE_AUTOPLAY = "ToggleAutoplay"
    TOGGLE_FULLSCREEN = "ToggleFullscreen"
    TOGGLE_ADVANCED_SETTINGS = "ToggleAdvancedSettings"
    ABOUT_DIALOG = "AboutDialog"
