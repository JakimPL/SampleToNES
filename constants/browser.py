# GUI Constants

# Window dimensions
DIM_WINDOW_MAIN_WIDTH = 1200
DIM_WINDOW_MAIN_HEIGHT = 800

# Layout dimensions
DIM_PANEL_LEFT_GAP = 20
DIM_PANEL_LEFT_WIDTH = 320
DIM_PANEL_LEFT_HEIGHT = -1
DIM_PANEL_RIGHT_WIDTH = 400
DIM_PANEL_RIGHT_HEIGHT = -1
DIM_PANEL_INSTRUCTION_DETAILS_WIDTH = 300
DIM_PANEL_RECONSTRUCTION_DETAILS_WIDTH = 400
DIM_PANEL_CONFIG_WIDTH = DIM_PANEL_LEFT_WIDTH - DIM_PANEL_LEFT_GAP
DIM_PANEL_CONFIG_HEIGHT = 0
DIM_PANEL_LIBRARY_WIDTH = DIM_PANEL_LEFT_WIDTH - DIM_PANEL_LEFT_GAP
DIM_PANEL_LIBRARY_HEIGHT = -1
DIM_PANEL_RECONSTRUCTOR_HEIGHT = 0
DIM_PANEL_RECONSTRUCTOR_WIDTH = DIM_PANEL_LEFT_WIDTH - DIM_PANEL_LEFT_GAP
DIM_PANEL_BROWSER_WIDTH = DIM_PANEL_LEFT_WIDTH - DIM_PANEL_LEFT_GAP
DIM_PANEL_BROWSER_HEIGHT = -1

# File dialog dimensions
DIM_DIALOG_FILE_WIDTH = 600
DIM_DIALOG_FILE_HEIGHT = 400
DIM_DIALOG_ERROR_WIDTH = 350
DIM_DIALOG_ERROR_HEIGHT = 0
DIM_DIALOG_ERROR_WIDTH_WRAP = DIM_DIALOG_ERROR_WIDTH - 10
DIM_DIALOG_CONVERTER_WIDTH = 700
DIM_DIALOG_CONVERTER_HEIGHT = 0

# UI element dimensions
DIM_BUTTON_DEFAULT_HEIGHT = 23
DIM_TEXT_DEFAULT_HEIGHT = 19
DIM_WINDOW_TITLE_BAR_HEIGHT = 25
DIM_WINDOW_PADDING = 8
DIM_CONVERTER_BUTTON_WIDTH = -1
DIM_CONVERTER_BUTTON_SPACING = 10

# Plot dimensions
DIM_WAVEFORM_PLOT_HEIGHT = 200

# Search UI dimensions
DIM_SEARCH_INPUT_WIDTH = -80
DIM_SEARCH_BUTTON_WIDTH = -1
DIM_COPY_BUTTON_WIDTH = 60

# Input validation ranges
RNG_CONFIG_MIN_WORKERS = 1

# GUI Labels
TITLE_WINDOW_MAIN = "SampleToNES"

# Menu labels
LBL_MENU_FILE = "File"
LBL_MENU_SAVE_CONFIG = "Save configuration"
LBL_MENU_LOAD_CONFIG = "Load configuration"
LBL_MENU_RECONSTRUCT_FILE = "Reconstruct file"
LBL_MENU_RECONSTRUCT_DIRECTORY = "Reconstruct directory"
LBL_MENU_LOAD_RECONSTRUCTION = "Load reconstruction"
LBL_MENU_EXPORT_RECONSTRUCTION_WAV = "Export reconstruction as WAV"
LBL_MENU_EXPORT_RECONSTRUCTION_FTI = "Export reconstruction as FTI"
LBL_MENU_LOAD_AUDIO = "Load audio"
LBL_MENU_EXIT = "Exit"

# Tab labels
LBL_TAB_LIBRARY = "Library"
LBL_TAB_RECONSTRUCTION = "Reconstruction"
LBL_TAB_BROWSER = "Browse results"

# Section headers
LBL_SECTION_OUTPUT_DIRECTORY = "Output directory"
LBL_SECTION_GENERAL_SETTINGS = "General settings"
LBL_SECTION_LIBRARY_DIRECTORY = "Library directory"
LBL_SECTION_LIBRARY_SETTINGS = "Library settings"
LBL_SECTION_LIBRARY_PANEL = "Library"
LBL_SECTION_AUDIO_INPUT = "Audio input"
LBL_SECTION_GENERATOR_SELECTION = "Generators"
LBL_SECTION_WAVEFORM_DISPLAY = "Waveform display"
LBL_SECTION_SAVED_RECONSTRUCTIONS = "Saved reconstructions"
LBL_SECTION_RECONSTRUCTION_DETAILS = "Reconstruction details"
LBL_SECTION_FAMITRACKER_EXPORT = "FamiTracker export"

# Button labels
LBL_BUTTON_SELECT_OUTPUT_DIRECTORY = "Select output directory"
LBL_BUTTON_SELECT_LIBRARY_DIRECTORY = "Select library directory"
LBL_BUTTON_GENERATE_LIBRARY = "Generate library"
LBL_BUTTON_RECONSTRUCT_FILE = "Reconstruct file"
LBL_BUTTON_RECONSTRUCT_DIRECTORY = "Reconstruct directory"
LBL_BUTTON_REGENERATE_LIBRARY = "Regenerate library"
LBL_BUTTON_REFRESH_LIBRARIES = "Refresh libraries"
LBL_BUTTON_SELECT_AUDIO_FILE = "Select audio file"
LBL_BUTTON_START_RECONSTRUCTION = "Start reconstruction"
LBL_BUTTON_PLAY_ORIGINAL = "Play original"
LBL_BUTTON_PLAY_RECONSTRUCTION = "Play reconstruction"
LBL_BUTTON_EXPORT_WAV = "Export WAV"
LBL_BUTTON_REFRESH_LIST = "Refresh reconstructions"
LBL_BUTTON_CLEAR_SEARCH = "Clear"
LBL_BUTTON_CANCEL = "Cancel"
LBL_BUTTON_CLOSE = "Close"
LBL_BUTTON_LOAD = "Load"

# Checkbox labels
LBL_CHECKBOX_NORMALIZE_AUDIO = "Normalize audio"
LBL_CHECKBOX_QUANTIZE_AUDIO = "Quantize audio"
LBL_CHECKBOX_TRIANGLE = "Triangle"
LBL_CHECKBOX_PULSE_1 = "Pulse 1"
LBL_CHECKBOX_PULSE_2 = "Pulse 2"
LBL_CHECKBOX_NOISE = "Noise"

# Input field labels
LBL_INPUT_MAX_WORKERS = "Workers"
LBL_INPUT_SAMPLE_RATE = "Sample rate"
LBL_INPUT_CHANGE_RATE = "Change rate"
LBL_INPUT_SEARCH = "Search"

# Dialog titles
TITLE_DIALOG_SAVE_CONFIG = "Save configuration"
TITLE_DIALOG_LOAD_CONFIG = "Load configuration"
TITLE_DIALOG_LOAD_AUDIO = "Load audio"
TITLE_DIALOG_LOAD_RECONSTRUCTION = "Load reconstruction"
TITLE_DIALOG_RECONSTRUCT_FILE = "Reconstruct file"
TITLE_DIALOG_RECONSTRUCT_DIRECTORY = "Reconstruct directory"
TITLE_DIALOG_SELECT_LIBRARY_DIRECTORY = "Select library directory"
TITLE_DIALOG_SELECT_OUTPUT_DIRECTORY = "Select output directory"
TITLE_DIALOG_EXPORT_WAV = "Export WAV"
TITLE_DIALOG_EXPORT_FTI = "Export FTI"
TITLE_DIALOG_EXPORT_FTI_DIRECTORY = "Export FTI to directory"
TITLE_DIALOG_ERROR = "Error"
TITLE_DIALOG_CONFIG_STATUS = "Configuration Status"
TITLE_DIALOG_CONVERTER = "Reconstruction progress"
TITLE_DIALOG_FILE_NOT_FOUND = "File not found"
TITLE_DIALOG_LIBRARY_NOT_LOADED = "Library not loaded"

# Plot labels
LBL_PLOT_AUDIO_WAVEFORMS = "Audio waveforms"
LBL_PLOT_TIME_SAMPLES = "Time (samples)"
LBL_PLOT_AMPLITUDE = "Amplitude"
LBL_PLOT_ORIGINAL = "Original"
LBL_PLOT_RECONSTRUCTION = "Reconstruction"

# Status messages
MSG_CONFIG_PREVIEW_DEFAULT = "Load or modify configuration to see preview."
MSG_GLOBAL_NO_FILE_SELECTED = "No file selected."
MSG_GLOBAL_NO_DIRECTORY_SELECTED = "No directory selected."
MSG_GLOBAL_NO_RESULTS_FOUND = "No results found."
MSG_RECONSTRUCTION_SELECT_TO_VIEW = "Select a reconstruction to view details."
MSG_CONFIG_APPLIED_SUCCESSFULLY = "Configuration applied successfully."
MSG_CONFIG_SAVED_SUCCESSFULLY = "Configuration saved successfully."
MSG_CONFIG_LOADED_SUCCESSFULLY = "Configuration loaded successfully."
MSG_CONFIG_SAVE_ERROR = "Error saving configuration."
MSG_CONFIG_LOAD_ERROR = "Error loading configuration."
TPL_RECONSTRUCTION_COMPLETE = "Reconstruction complete. Total error: {:.4f}"
MSG_RECONSTRUCTION_SELECT_AUDIO_AND_CONFIG = "Please select audio file and apply configuration first."
MSG_LIBRARY_EXISTS = "Library exists."
MSG_LIBRARY_NOT_EXISTS = "Library does not exist."
MSG_LIBRARY_GENERATING = "Generating library..."
MSG_LIBRARY_GENERATED_SUCCESSFULLY = "Library generated successfully."
MSG_LIBRARY_NOT_LOADED = "Library is not loaded. Please load or generate a library."
MSG_LIBRARY_LOADING = "Library is loading..."
MSG_CONFIG_NOT_READY = "Configuration not ready."
MSG_CONFIG_PREVIEW = "Configuration preview."
LBL_LIBRARY_LIBRARIES = "Libraries"
LBL_BROWSER_RECONSTRUCTIONS = "Reconstructions"
LBL_LIBRARY_AVAILABLE_LIBRARIES = "Libraries"
TPL_LIBRARY_NOT_EXISTS = "Library {} doesn't exist."
MSG_LIBRARY_NO_VALID_INSTRUCTIONS = "No valid instructions found."
MSG_GLOBAL_WINDOW_NOT_AVAILABLE = "Window not available."
MSG_LIBRARY_ERROR_GENERATING = "Error generating library."
MSG_WAVEFORM_NO_RECONSTRUCTION = (
    "No reconstruction loaded. Select a reconstruction from the list to display its waveform."
)
MSG_LIBRARY_FILE_NOT_FOUND = "The library file could not be found."
MSG_RECONSTRUCTION_FILE_NOT_FOUND = "The reconstruction file could not be found."
MSG_RECONSTRUCTION_AUDIO_FILE_NOT_FOUND = "The audio file of this reconstruction could not be found."

# Template strings
TPL_LIBRARY_EXISTS = "Library {} exists."
TPL_LIBRARY_LOADED = "Library {} loaded."
TPL_LIBRARY_TAG = "lib_{}"
TPL_GENERATOR_TAG = "generator_{}_{}"
TPL_GROUP_TAG = "{}_{}_{}"
TPL_GROUP_LABEL = "{} ({} item(s))"

# GUI element tags
TAG_LIBRARY_PANEL = "library_panel"
TAG_LIBRARY_STATUS = "library_status"
TAG_LIBRARY_CONTROLS_GROUP = "library_controls_group"
TAG_BROWSER_CONTROLS_GROUP = "browser_controls_group"
TAG_LIBRARY_BUTTON_GENERATE = "generate_library_button"
TAG_LIBRARY_PROGRESS = "library_progress"
TAG_LIBRARY_DIRECTORY_DISPLAY = "library_directory_display"
TAG_BROWSER_BUTTON_RECONSTRUCT_FILE = "browser_reconstruct_file_button"
TAG_BROWSER_BUTTON_RECONSTRUCT_DIRECTORY = "browser_reconstruct_directory_button"
TAG_OUTPUT_DIRECTORY_DISPLAY = "output_directory_display"
TAG_CONFIG_STATUS_POPUP = "config_status_popup"
TAG_CONFIG_PANEL = "config_panel"
TAG_CONFIG_PREVIEW = "config_preview"
TAG_CONFIG_NORMALIZE = "normalize"
TAG_CONFIG_QUANTIZE = "quantize"
TAG_CONFIG_MAX_WORKERS = "max_workers"
TAG_CONFIG_SAMPLE_RATE = "sample_rate"
TAG_CONFIG_CHANGE_RATE = "change_rate"
TAG_LIBRARY_TREE = "libraries_tree"
TAG_LIBRARY_TREE_GROUP = "libraries_tree_group"
TAG_LIBRARY_NOT_LOADED_DIALOG = "library_not_loaded_dialog"
TAG_RECONSTRUCTION_NOT_LOADED_DIALOG = "reconstruction_not_loaded_dialog"

# Indices and offsets
IDX_DIALOG_FIRST_SELECTION = 0
VAL_GLOBAL_DEFAULT_SLOT = 1
VAL_GLOBAL_DEFAULT_FLOAT = 0.0
VAL_GLOBAL_PROGRESS_COMPLETE = 1.0

# Dictionary keys
KEY_DIALOG_SELECTIONS = "selections"

# Main GUI tags
TAG_WINDOW_MAIN = "main_window"
TAG_TAB_BAR_MAIN = "main_tab_bar"
TAG_TAB_LIBRARY = "tab_library"
TAG_TAB_RECONSTRUCTION = "tab_reconstruction"
TAG_GLOBAL_LEFT_PANELS_GROUP = "left_panels_group"
TAG_CONFIG_PANEL_GROUP = "config_panel_group"
TAG_LIBRARY_PANEL_GROUP = "library_panel_group"
TAG_INSTRUCTION_PANEL = "instruction_panel"
TAG_INSTRUCTION_PANEL_GROUP = "instruction_panel_group"
TAG_INSTRUCTION_DETAILS_PANEL_GROUP = "instruction_details_panel_group"
TAG_INSTRUCTION_PLAYER_PANEL = "instruction_player_panel"
TAG_INSTRUCTION_WAVEFORM_DISPLAY = "instruction_waveform_display"
TAG_INSTRUCTION_SPECTRUM_DISPLAY = "instruction_spectrum_display"
TAG_INSTRUCTION_DETAILS_INFO = "instruction_details_info"
TAG_INSTRUCTION_DETAILS = "instruction_details"
TAG_RECONSTRUCTION_PROGRESS = "reconstruction_progress"
TAG_WAVEFORM_PLOT = "waveform_plot"
TAG_PLOT_X_AXIS = "x_axis"
TAG_PLOT_Y_AXIS = "y_axis"
TAG_RECONSTRUCTION_INFO = "reconstruction_info"
TAG_BROWSER_RECONSTRUCTION_LIST = "reconstruction_list"
TAG_BROWSER_RECONSTRUCTION_DETAILS = "reconstruction_details"
TAG_BROWSER_FAMITRACKER_EXPORT = "famitracker_export"
TAG_DIALOG_ERROR_LIBRARY_GENERATION = "error_dialog_library_generation"
TAG_CONFIG_LOAD_ERROR_DIALOG = "config_load_error_dialog"
TAG_CONVERTER_WINDOW = "converter_window"
TAG_CONVERTER_PROGRESS = "converter_progress"
TAG_CONVERTER_STATUS = "converter_status"
TAG_CONVERTER_INPUT_PATH_TEXT = "converter_input_path_text"
TAG_CONVERTER_OUTPUT_PATH_TEXT = "converter_output_path_text"
TAG_CONVERTER_LOAD_BUTTON = "converter_load_button"
TAG_CONVERTER_CANCEL_BUTTON = "converter_cancel_button"
TAG_CONVERTER_ERROR_DIALOG = "converter_error_dialog"
TAG_CONVERTER_SUCCESS_DIALOG = "converter_success_dialog"
TAG_RECONSTRUCTION_DETAILS_PANEL_GROUP = "reconstruction_details_panel_group"
TAG_FILE_NOT_FOUND_DIALOG = "file_not_found_dialog"
TAG_ERROR_DIALOG = "error_dialog"


# Messages
MSG_RECONSTRUCTION_INFO = "Reconstruction info"
MSG_CONFIG_ERROR = "Configuration error - please check settings"
MSG_CONVERTER_PROCESSING = "Processing: {}"
MSG_CONVERTER_ERROR = "Reconstruction failed."
MSG_CONVERTER_SUCCESS = "Reconstruction completed successfully!"
MSG_CONVERTER_CONFIG_NOT_AVAILABLE = "Configuration not available"
MSG_CONVERTER_COMPLETED = "Reconstruction completed!"
MSG_CONVERTER_IDLE = "Waiting to start..."
MSG_CONVERTER_CANCELLING = "Aborting the conversion..."
MSG_CONVERTER_CANCELLED = "Conversion cancelled."
TPL_CONVERTER_STATUS = "Progress: {}/{} files"
MSG_INPUT_PATH_PREFIX = "Input:"
MSG_OUTPUT_PATH_PREFIX = "Output:"

# Template strings
TPL_RECONSTRUCTION_GEN_TAG = "gen_{}"

# File dialog settings
VAL_DIALOG_FILE_COUNT_SINGLE = 1
VAL_DIALOG_DEFAULT_FILENAME_CONFIG = "config"

# Plot settings
VAL_PLOT_WIDTH_FULL = -1
VAL_PLOT_CHILDREN_SLOT = 2

# Waveform display settings
DIM_WAVEFORM_DEFAULT_HEIGHT = 300
CLR_WAVEFORM_LAYER_SAMPLE = (100, 200, 255, 255)
CLR_WAVEFORM_LAYER_RECONSTRUCTION = (255, 200, 100, 255)
CLR_WAVEFORM_POSITION_INDICATOR = (255, 255, 255, 255)
VAL_WAVEFORM_SAMPLE_THICKNESS = 1.5
VAL_WAVEFORM_RECONSTRUCTION_THICKNESS = 1.2
VAL_WAVEFORM_POSITION_INDICATOR_THICKNESS = 2.0
VAL_WAVEFORM_ZOOM_FACTOR = 1.1
VAL_WAVEFORM_DEFAULT_Y_MIN = -1.0
VAL_WAVEFORM_DEFAULT_Y_MAX = 1.0
VAL_WAVEFORM_AXIS_SLOT = 1
SUF_WAVEFORM_POSITION_INDICATOR = "_position_indicator"

# Converter window settings
CLR_PATH_TEXT = (100, 150, 255)
CLR_PATH_TEXT_HOVER = (150, 200, 255)
SUF_CONVERTER_HANDLER = "_handler"

# Waveform labels and messages
LBL_WAVEFORM_DISPLAY = "Waveform display"
LBL_WAVEFORM_TIME_LABEL = "Time (samples)"
LBL_WAVEFORM_AMPLITUDE_LABEL = "Amplitude"
LBL_WAVEFORM_SAMPLE_LAYER_NAME = "Sample"
LBL_WAVEFORM_RECONSTRUCTION_LAYER_NAME = "Reconstruction"
FMT_WAVEFORM_VALUE = "{}[{}] = {:.4f}"
FMT_WAVEFORM_FREQUENCY = "{:.2f} Hz"

# Button labels for waveform
LBL_WAVEFORM_BUTTON_RESET_X = "Reset X"
LBL_WAVEFORM_BUTTON_RESET_Y = "Reset Y"
LBL_WAVEFORM_BUTTON_RESET_ALL = "Reset all"
LBL_WAVEFORM_BUTTON_PLAY_AUDIO = "Play audio"

# Numeric constants for waveform
VAL_WAVEFORM_FREQUENCY_DECIMALS = 2
VAL_WAVEFORM_VALUE_DECIMALS = 4
VAL_WAVEFORM_POSITION_DECIMALS = 2

# Boolean values
FLAG_CHECKBOX_DEFAULT_ENABLED = True
FLAG_WINDOW_PRIMARY_ENABLED = True

# Empty label
LBL_GLOBAL_EMPTY = ""

# Audio player constants
DIM_PLAYER_PANEL_WIDTH = -1
DIM_PLAYER_PANEL_HEIGHT = 60
DIM_PLAYER_BUTTON_WIDTH = 80
LBL_PLAYER_BUTTON_PLAY = "Play"
LBL_PLAYER_BUTTON_PAUSE = "Pause"
LBL_PLAYER_BUTTON_RESUME = "Resume"
LBL_PLAYER_BUTTON_STOP = "Stop"
MSG_PLAYER_NO_AUDIO_LOADED = "No audio loaded."
MSG_PLAYER_AUDIO_PLAYBACK_ERROR = "Audio playback error"
TITLE_DIALOG_NO_AUDIO = "No Audio"
TITLE_DIALOG_PLAYBACK_ERROR = "Playback error."

# Instruction panel constants
MSG_INSTRUCTION_DETAILS = "Instruction details"
MSG_INSTRUCTION_NO_SELECTION = "No instruction selected."
LBL_INSTRUCTION_WAVEFORM = "Instruction waveform"
LBL_INSTRUCTION_SPECTRUM = "Instruction spectrum"

# Reconstruction panel constants
TAG_RECONSTRUCTION_PANEL = "reconstruction_panel"
TAG_RECONSTRUCTION_PLAYER_PANEL = "reconstruction_player_panel"
TAG_RECONSTRUCTION_WAVEFORM_DISPLAY = "reconstruction_waveform_display"
TAG_RECONSTRUCTION_DETAILS_PANEL = "reconstruction_details_panel"
TAG_RECONSTRUCTION_EXPORT_PANEL = "reconstruction_export_panel"
TAG_RECONSTRUCTION_PITCH_BAR_PLOT = "reconstruction_pitch_bar_plot"
TAG_RECONSTRUCTION_DETAILS_TAB_BAR = "reconstruction_details_tab_bar"
TAG_RECONSTRUCTION_EXPORT_FTI_BUTTON = "reconstruction_export_fti_button"
TAG_RECONSTRUCTION_GENERATORS_GROUP = "reconstruction_generators_group"
TAG_RECONSTRUCTION_AUDIO_SOURCE_GROUP = "reconstruction_audio_source_group"
TPL_RECONSTRUCTION_GENERATOR_CHECKBOX = "reconstruction_generator_{}"
TPL_RECONSTRUCTION_AUDIO_SOURCE_RADIO = "reconstruction_audio_source_{}"
TAG_RECONSTRUCTION_EXPORT_WAV_BUTTON = "reconstruction_export_wav_button"
TAG_RECONSTRUCTION_EXPORT_WAV_STATUS_POPUP = "reconstruction_export_wav_status_popup"
LBL_RECONSTRUCTION_WAVEFORM = "Reconstruction waveform"
LBL_RECONSTRUCTION_AUDIO_SOURCE = "Play audio source:"
LBL_RECONSTRUCTION_DETAILS = "Reconstruction details"
LBL_RECONSTRUCTION_EXPORT = "Export"
LBL_RECONSTRUCTION_EXPORT_FTI = "Export instrument to FTI"
LBL_RECONSTRUCTION_EXPORT_WAV = "Export reconstruction to WAV"
LBL_RECONSTRUCTION_PITCH_PLOT = "Pitch"
LBL_RECONSTRUCTION_HI_PITCH_PLOT = "Hi-pitch"
LBL_RECONSTRUCTION_VOLUME_PLOT = "Volume"
LBL_RECONSTRUCTION_ARPEGGIO_PLOT = "Arpeggio"
LBL_RECONSTRUCTION_DUTY_CYCLE_PLOT = "Duty cycle"
LBL_RECONSTRUCTION_INITIAL_PITCH = "Initial pitch: {}"
SUF_RECONSTRUCTION_AUDIO = "_audio"
SUF_RECONSTRUCTION_PLOT = "_plot"
SUF_SEARCH_BUTTON = "_search_button"
SUF_SEARCH_INPUT = "_search_input"
SUF_GROUP = "_group"
LBL_COPY_BUTTON = "Copy"
LBL_COPIED_TOOLTIP = "Copied!"
LBL_RADIO_ORIGINAL_AUDIO = "Original audio"
LBL_RADIO_RECONSTRUCTION_AUDIO = "Reconstruction"
MSG_RECONSTRUCTION_NO_SELECTION = "No reconstruction selected."
MSG_RECONSTRUCTION_NO_DATA = "No reconstruction loaded."
MSG_RECONSTRUCTION_EXPORT_SUCCESS = "Reconstruction saved successfully."
MSG_RECONSTRUCTION_EXPORT_NO_DATA = "No reconstruction loaded."
TPL_RECONSTRUCTION_EXPORT_ERROR = "Export error: {}"
TPL_ERROR = "Error: {}"
TITLE_DIALOG_RECONSTRUCTION_EXPORT_STATUS = "Export status"
TITLE_DIALOG_RECONSTRUCTION_NOT_LOADED = "Reconstruction not loaded"
VAL_AUDIO_SOURCE_SELECTOR = "selector"

# Waveform layer colors
CLR_WAVEFORM_DEFAULT = (255, 255, 255, 255)

# Waveform component suffixes
SUF_GRAPH_PLOT = "_plot"
SUF_GRAPH_X_AXIS = "_x_axis"
SUF_GRAPH_Y_AXIS = "_y_axis"
SUF_GRAPH_LEGEND = "_legend"
SUF_GRAPH_CONTROLS = "_controls"
SUF_GRAPH_INFO = "_info"
SUF_GRAPH_RAW_DATA = "_raw_data"
SUF_GRAPH_COPY_BUTTON = "_copy_button"
SUF_GRAPH_RAW_DATA_GROUP = "_raw_data_group"
SUF_BAR_PLOT_ZERO_LINE = "_zero_line"
SUF_SEPARATOR = "_separator"
SUF_NO_DATA_MESSAGE = "_no_data_message"
SUF_WINDOW = "_window"
SUF_CENTER_PANEL = "_center_panel"

# Spectrum display settings
LBL_SPECTRUM_DISPLAY = "Spectrum display"
VAL_SPECTRUM_LOG_OFFSET = 1e-2
VAL_SPECTRUM_GRAYSCALE_MAX = 255
LBL_SPECTRUM_X_AXIS = ""
LBL_SPECTRUM_Y_AXIS = "Frequency"

DIM_GRAPH_DEFAULT_WIDTH = -1
DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT = 300

# Boolean text values
LBL_GLOBAL_YES = "Yes"
LBL_GLOBAL_NO = "No"

# Default axis range
VAL_GRAPH_DEFAULT_X_MIN = 0.0
VAL_GRAPH_DEFAULT_X_MAX = 1.0

# Format precision
VAL_WAVEFORM_FLOAT_PRECISION = 4

# Audio player component suffixes
SUF_PLAYER_PLAY = "_play"
SUF_PLAYER_PAUSE = "_pause"
SUF_PLAYER_STOP = "_stop"
SUF_PLAYER_POSITION = "_position"
SUF_PLAYER_CONTROLS_GROUP = "_controls_group"
SUF_PLAYER_NO_AUDIO_POPUP = "_no_audio_popup"
SUF_PLAYER_ERROR_POPUP = "_error_popup"

# Audio player text constants
PFX_PLAYER_POSITION = "Position: "
SUF_PLAYER_SAMPLES = " samples"
LBL_BUTTON_OK = "OK"

# Instruction display text constants
PFX_INSTRUCTION_GENERATOR = "Generator: "
PFX_INSTRUCTION_NAME = "Instruction: "
PFX_INSTRUCTION_FREQUENCY = "Frequency: "
FMT_INSTRUCTION_FREQUENCY = "{:.2f} Hz"
MSG_INSTRUCTION_NO_FREQUENCY = "No frequency data available."
PFX_INSTRUCTION_SAMPLE_LENGTH = "Sample length: "
SUF_INSTRUCTION_SAMPLE_LENGTH = " samples"
PFX_INSTRUCTION_OFFSET = "Offset: "
LBL_INSTRUCTION_PARAMETERS_HEADER = "Instruction parameters:"
PFX_INSTRUCTION_PARAMETER_INDENT = "  "
VAL_INSTRUCTION_FLOAT_PRECISION = 4
SUF_INSTRUCTION_WAVEFORM = "_waveform"
SUF_INSTRUCTION_SPECTRUM = "_spectrum"

# Reconstructor panel constants
TAG_RECONSTRUCTION_PANEL_GROUP = "reconstruction_panel_group"
TAG_RECONSTRUCTOR_PANEL = "reconstructor_panel"
TAG_RECONSTRUCTOR_PANEL_GROUP = "reconstructor_panel_group"
LBL_SECTION_RECONSTRUCTOR_SETTINGS = "Reconstructor settings"
LBL_SLIDER_RECONSTRUCTOR_MIXER = "Mixer volume"
LBL_SLIDER_CONFIG_TRANSFORMATION_GAMMA = "Transformation gamma"
TAG_CONFIG_TRANSFORMATION_GAMMA = "transformation_gamma"
TAG_RECONSTRUCTOR_MIXER = "mixer"

# Browser panel constants
LBL_OUTPUT_AVAILABLE_RECONSTRUCTIONS = "Reconstructions"
TAG_BROWSER_PANEL = "browser_panel"
TAG_BROWSER_TREE = "browser_tree"
TAG_BROWSER_TREE_GROUP = "browser_tree_group"
TAG_BROWSER_PANEL_GROUP = "browser_panel_group"

# Node type constants
NOD_TYPE_ROOT = "root"
NOD_TYPE_LIBRARY = "library"
NOD_TYPE_LIBRARY_PLACEHOLDER = "library_placeholder"
NOD_TYPE_GENERATOR = "generator"
NOD_TYPE_GROUP = "group"
NOD_TYPE_INSTRUCTION = "instruction"
NOD_TYPE_DIRECTORY = "directory"
NOD_TYPE_FILE = "file"

# Node labels
NOD_LABEL_NOT_LOADED = "Not loaded"
NOD_LABEL_LIBRARIES = "Libraries"

# File extensions
EXT_FILE_JSON = ".json"
EXT_FILE_LIBRARY = ".dat"
EXT_FILE_FTI = ".fti"
EXT_FILE_WAV = ".wav"

# Bar plot display settings
LBL_BAR_PLOT_DISPLAY = "Bar plot display"
LBL_BAR_PLOT_VALUE_LABEL = "Value"
MSG_BAR_PLOT_NO_DATA = "No data loaded."
CLR_BAR_PLOT_DEFAULT = (100, 200, 255, 255)
CLR_BAR_PLOT_PITCH = (100, 200, 255, 255)
CLR_BAR_PLOT_VOLUME = (100, 255, 100, 255)
CLR_BAR_PLOT_ARPEGGIO = (255, 150, 100, 255)
CLR_BAR_PLOT_DUTY_CYCLE = (255, 200, 100, 255)
CLR_BAR_PLOT_ZERO_LINE = (200, 200, 200, 255)
VAL_BAR_PLOT_DEFAULT_X_MIN = 0.0
VAL_BAR_PLOT_DEFAULT_Y_MIN = 0.0
VAL_BAR_PLOT_DEFAULT_Y_MAX = 100.0
VAL_BAR_PLOT_PITCH_Y_MIN = -128.0
VAL_BAR_PLOT_PITCH_Y_MAX = 127.0
VAL_BAR_PLOT_VOLUME_Y_MIN = 0.0
VAL_BAR_PLOT_VOLUME_Y_MAX = 15.0
VAL_BAR_PLOT_DUTY_CYCLE_Y_MIN = 0.0
VAL_BAR_PLOT_DUTY_CYCLE_Y_MAX = 3.0
VAL_BAR_PLOT_AXIS_SLOT = 1
VAL_BAR_PLOT_BAR_WEIGHT = 0.8
VAL_BAR_PLOT_ZERO_LINE_THICKNESS = 1.0
DIM_BAR_PLOT_DEFAULT_HEIGHT = 200
