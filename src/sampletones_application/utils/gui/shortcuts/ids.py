from enum import Enum
from typing import Dict, Final

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.trackers.format import TrackerFormat


class ShortcutId(Enum):
    NEW_PROJECT = "NewProject"
    OPEN_PROJECT = "OpenProject"
    SAVE_PROJECT = "SaveProject"
    SAVE_PROJECT_AS = "SaveProjectAs"
    PROJECT_PROPERTIES = "ProjectProperties"
    EXPORT_PROJECT_FAMITRACKER = "ExportProjectFamiTracker"
    EXPORT_PROJECT_BITPHASE = "ExportProjectBitphase"
    CLOSE_PROJECT = "CloseProject"
    EXIT = "Exit"
    UNDO = "Undo"
    REDO = "Redo"
    RECONSTRUCT_FILE = "ReconstructFile"
    RECONSTRUCT_DIRECTORY = "ReconstructDirectory"
    LOAD_GENERATION_SETTINGS = "LoadGenerationSettings"
    SAVE_GENERATION_SETTINGS = "SaveGenerationSettings"
    OPEN_RECONSTRUCTION = "OpenReconstruction"
    SAVE_RECONSTRUCTION = "SaveReconstruction"
    SAVE_RECONSTRUCTION_AS = "SaveReconstructionAs"
    CLOSE_RECONSTRUCTION = "CloseReconstruction"
    EXPORT_RECONSTRUCTION_WAV = "ExportReconstructionWav"
    EXPORT_INSTRUMENTS_FAMITRACKER = "ExportInstrumentsFamiTracker"
    EXPORT_INSTRUMENTS_BITPHASE_PRESET = "ExportInstrumentsBitphasePreset"
    ADD_RECONSTRUCTION_TO_SEQUENCER = "AddReconstructionToSequencer"
    OPEN_RECONSTRUCTION_IN_EXPLORER = "OpenReconstructionInExplorer"
    LOCATE_ORIGINAL_AUDIO = "LocateOriginalAudio"
    PLAY = "Play"
    PLAY_FROM_START = "PlayFromStart"
    PLAY_FROM_FRAME = "PlayFromFrame"
    STOP = "Stop"
    TOGGLE_AUTOPLAY = "ToggleAutoplay"
    TOGGLE_FOLLOW_PLAYBACK = "ToggleFollowPlayback"
    TOGGLE_LOOP_SONG = "ToggleLoopSong"
    TOGGLE_CHANNEL_PULSE_1 = "ToggleChannelPulse1"
    TOGGLE_CHANNEL_PULSE_2 = "ToggleChannelPulse2"
    TOGGLE_CHANNEL_TRIANGLE = "ToggleChannelTriangle"
    TOGGLE_CHANNEL_NOISE = "ToggleChannelNoise"
    UNMUTE_ALL_CHANNELS = "UnmuteAllChannels"
    AUDIO_SETTINGS = "AudioSettings"
    TOGGLE_ADVANCED_SETTINGS = "ToggleAdvancedSettings"
    TOGGLE_FULLSCREEN = "ToggleFullscreen"
    ABOUT_DIALOG = "AboutDialog"
    NEXT_TAB = "NextTab"
    PREVIOUS_TAB = "PreviousTab"


CHANNEL_SHORTCUT_IDS: Final[Dict[GeneratorName, ShortcutId]] = {
    GeneratorName.PULSE1: ShortcutId.TOGGLE_CHANNEL_PULSE_1,
    GeneratorName.PULSE2: ShortcutId.TOGGLE_CHANNEL_PULSE_2,
    GeneratorName.TRIANGLE: ShortcutId.TOGGLE_CHANNEL_TRIANGLE,
    GeneratorName.NOISE: ShortcutId.TOGGLE_CHANNEL_NOISE,
}

PROJECT_EXPORT_SHORTCUT_IDS: Final[Dict[TrackerFormat, ShortcutId]] = {
    TrackerFormat.FAMITRACKER: ShortcutId.EXPORT_PROJECT_FAMITRACKER,
    TrackerFormat.BITPHASE: ShortcutId.EXPORT_PROJECT_BITPHASE,
}

SAMPLE_EXPORT_SHORTCUT_IDS: Final[Dict[TrackerFormat, ShortcutId]] = {
    TrackerFormat.FAMITRACKER: ShortcutId.EXPORT_INSTRUMENTS_FAMITRACKER,
    TrackerFormat.BITPHASE_PRESET: ShortcutId.EXPORT_INSTRUMENTS_BITPHASE_PRESET,
}
