from sampletones_application.categories.abstract import AbstractElement


class DialogElements(AbstractElement):
    OK = "ok"
    EXIT = "exit"
    DISCARD = "discard"
    CLOSE = "close"
    SAVE = "save"
    CANCEL = "cancel"
    COPIED = "copied"
    YES = "yes"
    NO = "no"
    UNTITLED = "untitled"


class TracebackElements(AbstractElement):
    COPY = "copy"
    SHOW = "show"
    HIDE = "hide"


class TreeElements(AbstractElement):
    ROOT = "root"
    SEARCH = "search"
    FILTER = "filter"
    CLEAR_SEARCH = "clear_search"


class ContextElements(AbstractElement):
    MARK_AS_FAVORITE = "mark_as_favorite"
    UNMARK_AS_FAVORITE = "unmark_as_favorite"
    COPY_FILENAME = "copy_filename"
    COPY_PATH = "copy_path"
    OPEN_IN_EXPLORER = "open_in_explorer"
    ADD_TO_SEQUENCER = "add_to_sequencer"
    TRIANGLE = "triangle"
    PULSE_1 = "pulse_1"
    PULSE_2 = "pulse_2"
    NOISE = "noise"


class MenuElements(AbstractElement):
    GROUP_GENERAL = "group_general"
    ITEM_CONFIG_SAVE = "item_config_save"
    ITEM_CONFIG_LOAD = "item_config_load"
    ITEM_AUDIO_SETTINGS = "item_audio_settings"
    ITEM_EXIT = "item_exit"
    GROUP_PROJECT = "group_project"
    ITEM_PROJECT_NEW = "item_project_new"
    ITEM_PROJECT_OPEN = "item_project_open"
    ITEM_PROJECT_SAVE = "item_project_save"
    ITEM_PROJECT_SAVE_AS = "item_project_save_as"
    ITEM_PROJECT_CLOSE = "item_project_close"
    GROUP_RECONSTRUCTION = "group_reconstruction"
    GROUP_CONFIGURATION = "group_configuration"
    ITEM_RECONSTRUCTION_RECONSTRUCT_FILE = "item_reconstruction_reconstruct_file"
    ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY = "item_reconstruction_reconstruct_directory"
    ITEM_RECONSTRUCTION_SAVE = "item_reconstruction_save"
    ITEM_RECONSTRUCTION_SAVE_AS = "item_reconstruction_save_as"
    ITEM_RECONSTRUCTION_LOAD = "item_reconstruction_load"
    ITEM_RECONSTRUCTION_CLOSE = "item_reconstruction_close"
    ITEM_RECONSTRUCTION_EXPORT_WAV = "item_reconstruction_export_wav"
    ITEM_RECONSTRUCTION_EXPORT_FTIS = "item_reconstruction_export_ftis"
    GROUP_PLAYBACK = "group_playback"
    ITEM_PLAYBACK_PLAY_FROM_START = "item_playback_play_from_start"
    ITEM_PLAYBACK_PLAY = "item_playback_play"
    ITEM_PLAYBACK_PAUSE = "item_playback_pause"
    ITEM_PLAYBACK_RESUME = "item_playback_resume"
    ITEM_PLAYBACK_STOP = "item_playback_stop"
    ITEM_PLAYBACK_AUTOPLAY = "item_playback_autoplay"
    GROUP_VIEW = "group_view"
    ITEM_VIEW_FULLSCREEN = "item_view_fullscreen"
    ITEM_VIEW_SHOW_ADVANCED_SETTINGS = "item_view_show_advanced_settings"
    TAB_MAIN = "tab_main"
    TAB_INSTRUCTIONS = "tab_instructions"
    TAB_RECONSTRUCTIONS = "tab_reconstructions"
    TAB_SEQUENCER = "tab_sequencer"


class StatusElements(AbstractElement):
    PATH = "path"
    NODE_RECONSTRUCTION_NO_AUTOPLAY = "node_reconstruction_no_autoplay"
    NODE_RECONSTRUCTION = "node_reconstruction"
    NODE_LIBRARY = "node_library"
    TREE_SEARCH = "tree_search"
    INPUT = "input"
    NODE_DIRECTORY = "node_directory"


class PlayerElements(AbstractElement):
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    POSITION_PREFIX = "position_prefix"
    SAMPLES_SUFFIX = "samples_suffix"
    NO_AUDIO_LOADED = "no_audio_loaded"
    AUDIO_PLAYBACK_ERROR = "audio_playback_error"
    NO_AUDIO_DIALOG_TITLE = "no_audio_dialog_title"


class GraphElements(AbstractElement):
    WAVEFORM_ORIGINAL = "waveform_original"
    WAVEFORM_RECONSTRUCTION = "waveform_reconstruction"
    WAVEFORM_DISPLAY = "waveform_display"
    WAVEFORM_TIME_AXIS = "waveform_time_axis"
    WAVEFORM_AMPLITUDE_AXIS = "waveform_amplitude_axis"
    WAVEFORM_SAMPLE_NAME = "waveform_sample_name"
    SPECTRUM_DISPLAY = "spectrum_display"
    SPECTRUM_X_AXIS = "spectrum_x_axis"
    SPECTRUM_FREQUENCY_AXIS = "spectrum_frequency_axis"
    SPECTRUM_NAME = "spectrum_name"
    BAR_DISPLAY = "bar_display"
    SPECTRUM_NAVIGATION = "spectrum_navigation"
    WAVEFORM_NAVIGATION = "waveform_navigation"


class GlobalMessageElements(AbstractElement):
    TREE_NO_RESULTS = "tree_no_results"
    INVALID_METADATA_ERROR = "invalid_metadata_error"
    RECONSTRUCTION_NO_DATA = "reconstruction_no_data"
    RECONSTRUCTION_SAVED_SUCCESSFULLY = "reconstruction_saved_successfully"
    RECONSTRUCTION_SAVE_FAILED = "reconstruction_save_failed"
    CONFIG_SAVE_FAILED = "config_save_failed"
    EXIT_CONVERSION_IN_PROGRESS = "exit_conversion_in_progress"
    EXIT_LIBRARY_GENERATION_IN_PROGRESS = "exit_library_generation_in_progress"
    EXIT_UNSAVED_RECONSTRUCTION = "exit_unsaved_reconstruction"
    CLOSE_UNSAVED_RECONSTRUCTION = "close_unsaved_reconstruction"
    LOAD_UNSAVED_RECONSTRUCTION = "load_unsaved_reconstruction"
    PROJECT_SAVED_SUCCESSFULLY = "project_saved_successfully"
    PROJECT_SAVE_FAILED = "project_save_failed"
    NEW_UNSAVED_PROJECT = "new_unsaved_project"
    OPEN_UNSAVED_PROJECT = "open_unsaved_project"
    CLOSE_UNSAVED_PROJECT = "close_unsaved_project"
    CONFIGURATION_SAVED_SUCCESSFULLY = "configuration_saved_successfully"
    CONFIGURATION_LOADED_SUCCESSFULLY = "configuration_loaded_successfully"
    CONFIGURATION_SAVE_ERROR = "configuration_save_error"
    CONFIGURATION_LOAD_ERROR = "configuration_load_error"
    CONFIGURATION_INVALID_ERROR = "configuration_invalid_error"
    AUDIO_PLAYBACK_ERROR = "audio_playback_error"
    ALL_AUDIO_FORMATS = "all_audio_formats"


class GlobalDialogTitleElements(AbstractElement):
    MAIN_WINDOW = "main_window"
    SAVE_CONFIG = "save_config"
    LOAD_CONFIG = "load_config"
    ERROR = "error"
    CONFIG_STATUS = "config_status"
    FILE_NOT_FOUND = "file_not_found"
    RECONSTRUCT_FILE = "reconstruct_file"
    RECONSTRUCT_DIRECTORY = "reconstruct_directory"
    EXIT_CONFIRMATION = "exit_confirmation"
    SAVE_RECONSTRUCTION = "save_reconstruction"
    RECONSTRUCTION_SAVED = "reconstruction_saved"
    CLOSE_UNSAVED_RECONSTRUCTION = "close_unsaved_reconstruction"
    LOAD_UNSAVED_RECONSTRUCTION = "load_unsaved_reconstruction"
    SAVE_PROJECT = "save_project"
    PROJECT_SAVED = "project_saved"
    NEW_UNSAVED_PROJECT = "new_unsaved_project"
    OPEN_UNSAVED_PROJECT = "open_unsaved_project"
    CLOSE_UNSAVED_PROJECT = "close_unsaved_project"


class GlobalTemplateElements(AbstractElement):
    TIME_ESTIMATION = "time_estimation"
    FPS = "fps"
    EXPAND = "expand"
    COLLAPSE = "collapse"
    ON = "on"
    OFF = "off"
