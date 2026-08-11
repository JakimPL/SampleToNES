from enum import Enum, StrEnum
from typing import Dict, Final, Self, Tuple

from sampletones_application.constants.playback import FollowMode
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.trackers.format import TrackerFormat


class ShortcutCategory(StrEnum):
    """The scope that answers an action's keys.

    Each category is a separate keyboard context, so one combination means one thing inside a
    category and is free to mean something else in another: Escape cancels a pending entry in the
    tracker and stops playback everywhere else. ``DIALOG`` is structural — Tab, Enter and Escape
    are how a modal is operated at all, which marks them as the set a keybindings editor leaves
    in place.
    """

    APPLICATION = "application"
    ORDER = "order"
    TRACKER = "tracker"
    SAMPLES = "samples"
    DIALOG = "dialog"


class ShortcutId(Enum):
    """Every named action a key press reaches, each declaring the category it belongs to.

    An id is the one name an action answers to: the scheme binds combinations to it, a menu asks
    it for the accelerator to print, and a panel asks it whether a press was meant for it. The
    value is the name a keybinding file writes; the category is code, since it follows from which
    scope handles the action rather than from a reader's preference.
    """

    category: ShortcutCategory

    def __new__(cls, value: str, category: ShortcutCategory) -> Self:
        member = object.__new__(cls)
        member._value_ = value
        member.category = category
        return member

    NEW_PROJECT = ("NewProject", ShortcutCategory.APPLICATION)
    OPEN_PROJECT = ("OpenProject", ShortcutCategory.APPLICATION)
    SAVE_PROJECT = ("SaveProject", ShortcutCategory.APPLICATION)
    SAVE_PROJECT_AS = ("SaveProjectAs", ShortcutCategory.APPLICATION)
    PROJECT_PROPERTIES = ("ProjectProperties", ShortcutCategory.APPLICATION)
    EXPORT_PROJECT_FAMITRACKER = ("ExportProjectFamiTracker", ShortcutCategory.APPLICATION)
    EXPORT_PROJECT_BITPHASE = ("ExportProjectBitphase", ShortcutCategory.APPLICATION)
    RENDER_SONG = ("RenderSong", ShortcutCategory.APPLICATION)
    CLOSE_PROJECT = ("CloseProject", ShortcutCategory.APPLICATION)
    EXIT = ("Exit", ShortcutCategory.APPLICATION)
    UNDO = ("Undo", ShortcutCategory.APPLICATION)
    REDO = ("Redo", ShortcutCategory.APPLICATION)
    RECONSTRUCT_FILE = ("ReconstructFile", ShortcutCategory.APPLICATION)
    RECONSTRUCT_DIRECTORY = ("ReconstructDirectory", ShortcutCategory.APPLICATION)
    LOAD_GENERATION_SETTINGS = ("LoadGenerationSettings", ShortcutCategory.APPLICATION)
    SAVE_GENERATION_SETTINGS = ("SaveGenerationSettings", ShortcutCategory.APPLICATION)
    OPEN_RECONSTRUCTION = ("OpenReconstruction", ShortcutCategory.APPLICATION)
    SAVE_RECONSTRUCTION = ("SaveReconstruction", ShortcutCategory.APPLICATION)
    SAVE_RECONSTRUCTION_AS = ("SaveReconstructionAs", ShortcutCategory.APPLICATION)
    CLOSE_RECONSTRUCTION = ("CloseReconstruction", ShortcutCategory.APPLICATION)
    EXPORT_RECONSTRUCTION_WAV = ("ExportReconstructionWav", ShortcutCategory.APPLICATION)
    EXPORT_INSTRUMENTS_FAMITRACKER = ("ExportInstrumentsFamiTracker", ShortcutCategory.APPLICATION)
    EXPORT_INSTRUMENTS_BITPHASE_PRESET = ("ExportInstrumentsBitphasePreset", ShortcutCategory.APPLICATION)
    ADD_RECONSTRUCTION_TO_SEQUENCER = ("AddReconstructionToSequencer", ShortcutCategory.APPLICATION)
    OPEN_RECONSTRUCTION_IN_EXPLORER = ("OpenReconstructionInExplorer", ShortcutCategory.APPLICATION)
    LOCATE_ORIGINAL_AUDIO = ("LocateOriginalAudio", ShortcutCategory.APPLICATION)
    PLAY = ("Play", ShortcutCategory.APPLICATION)
    PLAY_FROM_START = ("PlayFromStart", ShortcutCategory.APPLICATION)
    PLAY_FROM_FRAME = ("PlayFromFrame", ShortcutCategory.APPLICATION)
    STOP = ("Stop", ShortcutCategory.APPLICATION)
    TOGGLE_AUTOPLAY = ("ToggleAutoplay", ShortcutCategory.APPLICATION)
    FOLLOW_ROWS = ("FollowRows", ShortcutCategory.APPLICATION)
    FOLLOW_PATTERNS = ("FollowPatterns", ShortcutCategory.APPLICATION)
    FOLLOW_OFF = ("FollowOff", ShortcutCategory.APPLICATION)
    TOGGLE_LOOP_SONG = ("ToggleLoopSong", ShortcutCategory.APPLICATION)
    TOGGLE_CHANNEL_PULSE_1 = ("ToggleChannelPulse1", ShortcutCategory.APPLICATION)
    TOGGLE_CHANNEL_PULSE_2 = ("ToggleChannelPulse2", ShortcutCategory.APPLICATION)
    TOGGLE_CHANNEL_TRIANGLE = ("ToggleChannelTriangle", ShortcutCategory.APPLICATION)
    TOGGLE_CHANNEL_NOISE = ("ToggleChannelNoise", ShortcutCategory.APPLICATION)
    UNMUTE_ALL_CHANNELS = ("UnmuteAllChannels", ShortcutCategory.APPLICATION)
    AUDIO_SETTINGS = ("AudioSettings", ShortcutCategory.APPLICATION)
    DISPLAY_SETTINGS = ("DisplaySettings", ShortcutCategory.APPLICATION)
    KEYBOARD_SETTINGS = ("KeyboardSettings", ShortcutCategory.APPLICATION)
    TOGGLE_ADVANCED_SETTINGS = ("ToggleAdvancedSettings", ShortcutCategory.APPLICATION)
    TOGGLE_FULLSCREEN = ("ToggleFullscreen", ShortcutCategory.APPLICATION)
    ABOUT_DIALOG = ("AboutDialog", ShortcutCategory.APPLICATION)
    NEXT_TAB = ("NextTab", ShortcutCategory.APPLICATION)
    PREVIOUS_TAB = ("PreviousTab", ShortcutCategory.APPLICATION)

    ORDER_PREVIOUS_POSITION = ("OrderPreviousPosition", ShortcutCategory.ORDER)
    ORDER_NEXT_POSITION = ("OrderNextPosition", ShortcutCategory.ORDER)
    ORDER_PREVIOUS_CHANNEL = ("OrderPreviousChannel", ShortcutCategory.ORDER)
    ORDER_NEXT_CHANNEL = ("OrderNextChannel", ShortcutCategory.ORDER)
    ORDER_FIRST_POSITION = ("OrderFirstPosition", ShortcutCategory.ORDER)
    ORDER_LAST_POSITION = ("OrderLastPosition", ShortcutCategory.ORDER)
    ORDER_EXTEND_SELECTION_UP = ("OrderExtendSelectionUp", ShortcutCategory.ORDER)
    ORDER_EXTEND_SELECTION_DOWN = ("OrderExtendSelectionDown", ShortcutCategory.ORDER)
    ORDER_EXTEND_SELECTION_LEFT = ("OrderExtendSelectionLeft", ShortcutCategory.ORDER)
    ORDER_EXTEND_SELECTION_RIGHT = ("OrderExtendSelectionRight", ShortcutCategory.ORDER)
    ORDER_EXTEND_SELECTION_TO_FIRST_POSITION = (
        "OrderExtendSelectionToFirstPosition",
        ShortcutCategory.ORDER,
    )
    ORDER_EXTEND_SELECTION_TO_LAST_POSITION = (
        "OrderExtendSelectionToLastPosition",
        ShortcutCategory.ORDER,
    )
    ORDER_MOVE_FRAME_LEFT = ("OrderMoveFrameLeft", ShortcutCategory.ORDER)
    ORDER_MOVE_FRAME_RIGHT = ("OrderMoveFrameRight", ShortcutCategory.ORDER)
    ORDER_MOVE_FRAME_TO_START = ("OrderMoveFrameToStart", ShortcutCategory.ORDER)
    ORDER_MOVE_FRAME_TO_END = ("OrderMoveFrameToEnd", ShortcutCategory.ORDER)
    ORDER_ADD_FRAME = ("OrderAddFrame", ShortcutCategory.ORDER)
    ORDER_INSERT_FRAME = ("OrderInsertFrame", ShortcutCategory.ORDER)
    ORDER_REMOVE_FRAME = ("OrderRemoveFrame", ShortcutCategory.ORDER)
    ORDER_DUPLICATE_FRAME = ("OrderDuplicateFrame", ShortcutCategory.ORDER)
    ORDER_CLONE_FRAME = ("OrderCloneFrame", ShortcutCategory.ORDER)
    ORDER_CLEAR_FRAME = ("OrderClearFrame", ShortcutCategory.ORDER)
    ORDER_CLEAR_CELL = ("OrderClearCell", ShortcutCategory.ORDER)
    ORDER_CLEAR_PREVIOUS_CELL = ("OrderClearPreviousCell", ShortcutCategory.ORDER)
    ORDER_CANCEL_ENTRY = ("OrderCancelEntry", ShortcutCategory.ORDER)

    TRACKER_PREVIOUS_ROW = ("TrackerPreviousRow", ShortcutCategory.TRACKER)
    TRACKER_NEXT_ROW = ("TrackerNextRow", ShortcutCategory.TRACKER)
    TRACKER_PREVIOUS_SUBCOLUMN = ("TrackerPreviousSubcolumn", ShortcutCategory.TRACKER)
    TRACKER_NEXT_SUBCOLUMN = ("TrackerNextSubcolumn", ShortcutCategory.TRACKER)
    TRACKER_PREVIOUS_COLUMN = ("TrackerPreviousColumn", ShortcutCategory.TRACKER)
    TRACKER_NEXT_COLUMN = ("TrackerNextColumn", ShortcutCategory.TRACKER)
    TRACKER_FIRST_ROW = ("TrackerFirstRow", ShortcutCategory.TRACKER)
    TRACKER_LAST_ROW = ("TrackerLastRow", ShortcutCategory.TRACKER)
    TRACKER_EXTEND_SELECTION_UP = ("TrackerExtendSelectionUp", ShortcutCategory.TRACKER)
    TRACKER_EXTEND_SELECTION_DOWN = ("TrackerExtendSelectionDown", ShortcutCategory.TRACKER)
    TRACKER_EXTEND_SELECTION_LEFT = ("TrackerExtendSelectionLeft", ShortcutCategory.TRACKER)
    TRACKER_EXTEND_SELECTION_RIGHT = ("TrackerExtendSelectionRight", ShortcutCategory.TRACKER)
    TRACKER_EXTEND_SELECTION_TO_FIRST_ROW = (
        "TrackerExtendSelectionToFirstRow",
        ShortcutCategory.TRACKER,
    )
    TRACKER_EXTEND_SELECTION_TO_LAST_ROW = (
        "TrackerExtendSelectionToLastRow",
        ShortcutCategory.TRACKER,
    )
    TRACKER_PAGE_UP = ("TrackerPageUp", ShortcutCategory.TRACKER)
    TRACKER_PAGE_DOWN = ("TrackerPageDown", ShortcutCategory.TRACKER)
    TRACKER_CLEAR_ROW = ("TrackerClearRow", ShortcutCategory.TRACKER)
    TRACKER_CLEAR_PREVIOUS_ROW = ("TrackerClearPreviousRow", ShortcutCategory.TRACKER)
    TRACKER_CANCEL_ENTRY = ("TrackerCancelEntry", ShortcutCategory.TRACKER)
    TRACKER_PLAY_FROM_ROW = ("TrackerPlayFromRow", ShortcutCategory.TRACKER)

    SAMPLES_RENAME_SAMPLE = ("SamplesRenameSample", ShortcutCategory.SAMPLES)
    SAMPLES_REMOVE_SAMPLE = ("SamplesRemoveSample", ShortcutCategory.SAMPLES)
    SAMPLES_MOVE_SAMPLE_UP = ("SamplesMoveSampleUp", ShortcutCategory.SAMPLES)
    SAMPLES_MOVE_SAMPLE_DOWN = ("SamplesMoveSampleDown", ShortcutCategory.SAMPLES)
    SAMPLES_MOVE_SAMPLE_TO_TOP = ("SamplesMoveSampleToTop", ShortcutCategory.SAMPLES)
    SAMPLES_MOVE_SAMPLE_TO_BOTTOM = ("SamplesMoveSampleToBottom", ShortcutCategory.SAMPLES)
    SAMPLES_CANCEL_RENAME = ("SamplesCancelRename", ShortcutCategory.SAMPLES)

    DIALOG_NEXT_CONTROL = ("DialogNextControl", ShortcutCategory.DIALOG)
    DIALOG_PREVIOUS_CONTROL = ("DialogPreviousControl", ShortcutCategory.DIALOG)
    DIALOG_ACTIVATE = ("DialogActivate", ShortcutCategory.DIALOG)
    DIALOG_CANCEL = ("DialogCancel", ShortcutCategory.DIALOG)


SHORTCUT_IDS_BY_NAME: Final[Dict[str, ShortcutId]] = {shortcut_id.value: shortcut_id for shortcut_id in ShortcutId}

EDITABLE_SHORTCUT_CATEGORIES: Final[Tuple[ShortcutCategory, ...]] = tuple(
    category for category in ShortcutCategory if category is not ShortcutCategory.DIALOG
)

FOLLOW_MODE_SHORTCUT_IDS: Final[Dict[FollowMode, ShortcutId]] = {
    FollowMode.ROWS: ShortcutId.FOLLOW_ROWS,
    FollowMode.PATTERNS: ShortcutId.FOLLOW_PATTERNS,
    FollowMode.OFF: ShortcutId.FOLLOW_OFF,
}

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
