# GUI Constants

# Window dimensions
DIM_WINDOW_MAIN_WIDTH = 1200
DIM_WINDOW_MAIN_HEIGHT = 800

# Layout dimensions
DIM_PANEL_CONFIG_WIDTH = 300
DIM_PANEL_CONFIG_HEIGHT = 280
DIM_PANEL_LIBRARY_WIDTH = 300
DIM_PANEL_LIBRARY_HEIGHT = 400
DIM_PANEL_RECONSTRUCTION_WIDTH = 300
DIM_PANEL_RECONSTRUCTION_HEIGHT = 600
DIM_PANEL_BROWSER_WIDTH = 300
DIM_PANEL_BROWSER_HEIGHT = 600

# File dialog dimensions
DIM_DIALOG_FILE_WIDTH = 600
DIM_DIALOG_FILE_HEIGHT = 400

# Plot dimensions
DIM_WAVEFORM_PLOT_HEIGHT = 200

# Input validation ranges
RNG_CONFIG_MIN_WORKERS = 1

# Multiline text heights
DIM_FAMITRACKER_EXPORT_HEIGHT = 200

# GUI Labels
TITLE_WINDOW_MAIN = "SampleToNES Converter"

# Menu labels
LBL_MENU_FILE = "File"
LBL_MENU_LOAD_CONFIG = "Load configuration"
LBL_MENU_LOAD_AUDIO = "Load audio"
LBL_MENU_LOAD_RECONSTRUCTION = "Load reconstruction"
LBL_MENU_EXIT = "Exit"

# Tab labels
LBL_TAB_LIBRARY = "Library"
LBL_TAB_RECONSTRUCTION = "Reconstruction"
LBL_TAB_BROWSER = "Browse results"

# Section headers
LBL_SECTION_GENERAL_SETTINGS = "General settings"
LBL_SECTION_LIBRARY_DIRECTORY = "Library directory"
LBL_SECTION_LIBRARY_SETTINGS = "Library settings"
LBL_SECTION_LIBRARY_PANEL = "Library"
LBL_SECTION_AUDIO_INPUT = "Audio input"
LBL_SECTION_GENERATOR_SELECTION = "Generator selection"
LBL_SECTION_WAVEFORM_DISPLAY = "Waveform display"
LBL_SECTION_SAVED_RECONSTRUCTIONS = "Saved reconstructions"
LBL_SECTION_RECONSTRUCTION_DETAILS = "Reconstruction details"
LBL_SECTION_FAMITRACKER_EXPORT = "FamiTracker export"

# Button labels
LBL_BUTTON_SELECT_LIBRARY_DIR = "Select library directory"
LBL_BUTTON_GENERATE_LIBRARY = "Generate library"
LBL_BUTTON_REGENERATE_LIBRARY = "Regenerate library"
LBL_BUTTON_REFRESH_LIBRARIES = "Refresh libraries"
LBL_BUTTON_SELECT_AUDIO_FILE = "Select audio file"
LBL_BUTTON_START_RECONSTRUCTION = "Start reconstruction"
LBL_BUTTON_PLAY_ORIGINAL = "Play original"
LBL_BUTTON_PLAY_RECONSTRUCTION = "Play reconstruction"
LBL_BUTTON_EXPORT_WAV = "Export WAV"
LBL_BUTTON_REFRESH_LIST = "Refresh list"

# Checkbox labels
LBL_CHECKBOX_NORMALIZE_AUDIO = "Normalize audio"
LBL_CHECKBOX_QUANTIZE_AUDIO = "Quantize audio"
LBL_CHECKBOX_TRIANGLE = "Triangle"
LBL_CHECKBOX_PULSE_1 = "Pulse 1"
LBL_CHECKBOX_PULSE_2 = "Pulse 2"
LBL_CHECKBOX_NOISE = "Noise"

# Input field labels
LBL_INPUT_MAX_WORKERS = "Max workers"
LBL_INPUT_SAMPLE_RATE = "Sample rate"
LBL_INPUT_CHANGE_RATE = "Change rate"

# Dialog titles
TITLE_DIALOG_LOAD_CONFIG = "Load configuration"
TITLE_DIALOG_LOAD_AUDIO = "Load audio"
TITLE_DIALOG_LOAD_RECONSTRUCTION = "Load reconstruction"
TITLE_DIALOG_SELECT_LIBRARY_DIR = "Select library directory"
TITLE_DIALOG_EXPORT_WAV = "Export WAV"

# Plot labels
LBL_PLOT_AUDIO_WAVEFORMS = "Audio waveforms"
LBL_PLOT_TIME_SAMPLES = "Time (samples)"
LBL_PLOT_AMPLITUDE = "Amplitude"
LBL_PLOT_ORIGINAL = "Original"
LBL_PLOT_RECONSTRUCTION = "Reconstruction"

# Status messages
MSG_CONFIG_PREVIEW_DEFAULT = "Load or modify configuration to see preview"
MSG_GLOBAL_NO_FILE_SELECTED = "No file selected"
MSG_GLOBAL_NO_DIR_SELECTED = "No directory selected"
MSG_RECONSTRUCTION_SELECT_TO_VIEW = "Select a reconstruction to view details"
MSG_CONFIG_APPLIED_SUCCESSFULLY = "Configuration applied successfully"
TPL_RECONSTRUCTION_COMPLETE = "Reconstruction complete. Total error: {:.4f}"
MSG_RECONSTRUCTION_SELECT_AUDIO_AND_CONFIG = "Please select audio file and apply configuration first"
MSG_LIBRARY_EXISTS = "Library exists"
MSG_LIBRARY_NOT_EXISTS = "Library does not exist"
MSG_LIBRARY_GENERATING = "Generating library..."
MSG_LIBRARY_GENERATED_SUCCESSFULLY = "Library generated successfully"
MSG_LIBRARY_NOT_LOADED = "Library is not loaded"
MSG_LIBRARY_LOADING = "Library is loading..."
MSG_CONFIG_NOT_READY = "Configuration not ready"
MSG_CONFIG_PREVIEW = "Configuration preview"
LBL_LIBRARY_LIBRARIES = "Libraries"
LBL_LIBRARY_AVAILABLE_LIBRARIES = "Libraries"
TPL_LIBRARY_NOT_EXISTS = "Library {} does not exist."
MSG_LIBRARY_NO_VALID_INSTRUCTIONS = "No valid instructions found"
MSG_GLOBAL_WINDOW_NOT_AVAILABLE = "Window not available"
MSG_LIBRARY_ERROR_GENERATING = "generating library"

# File extensions
EXT_DIALOG_JSON = "*.json"
EXT_DIALOG_WAV = "*.wav"

# Default display values
TPL_LIBRARY_DEFAULT_DIR_DISPLAY = "Default: {}"
TPL_LIBRARY_CUSTOM_DIR_DISPLAY = "Custom: {}"
PFX_GLOBAL_ERROR = "Error: {}"
PFX_GLOBAL_LOADED = "Loaded: {}"

# Template strings
TPL_LIBRARY_EXISTS = "Library {} exists."
TPL_LIBRARY_TAG = "lib_{}"
TPL_GENERATOR_TAG = "generator_{}_{}"
TPL_GROUP_TAG = "{}_{}_{}"
TPL_GROUP_LABEL = "{} ({} item(s))"

# GUI element tags
TAG_LIBRARY_PANEL = "library_panel"
TAG_LIBRARY_STATUS = "library_status"
TAG_LIBRARY_CONTROLS_GROUP = "library_controls_group"
TAG_LIBRARY_BUTTON_GENERATE = "generate_library_button"
TAG_LIBRARY_PROGRESS = "library_progress"
TAG_LIBRARY_DIRECTORY_DISPLAY = "library_directory_display"
TAG_CONFIG_PREVIEW = "config_preview"
TAG_CONFIG_NORMALIZE = "normalize"
TAG_CONFIG_QUANTIZE = "quantize"
TAG_CONFIG_MAX_WORKERS = "max_workers"
TAG_CONFIG_SAMPLE_RATE = "sample_rate"
TAG_CONFIG_CHANGE_RATE = "change_rate"
TAG_LIBRARY_TREE = "libraries_tree"

# Indices and offsets
IDX_DIALOG_FIRST_SELECTION = 0
VAL_GLOBAL_DEFAULT_SLOT = 1
VAL_GLOBAL_DEFAULT_FLOAT = 0.0
VAL_GLOBAL_PROGRESS_COMPLETE = 1.0

# Dictionary keys
KEY_DIALOG_SELECTIONS = "selections"

# Main GUI tags
TAG_WINDOW_MAIN = "main_window"
TAG_GLOBAL_LEFT_PANELS_GROUP = "left_panels_group"
TAG_CONFIG_PANEL_GROUP = "config_panel_group"
TAG_LIBRARY_PANEL_GROUP = "library_panel_group"
TAG_CONFIG_TAB = "config_tab"
TAG_RECONSTRUCTION_SELECTED_AUDIO_FILE = "selected_audio_file"
TAG_RECONSTRUCTION_PROGRESS = "reconstruction_progress"
TAG_WAVEFORM_PLOT = "waveform_plot"
TAG_PLOT_X_AXIS = "x_axis"
TAG_PLOT_Y_AXIS = "y_axis"
TAG_RECONSTRUCTION_INFO = "reconstruction_info"
TAG_BROWSER_RECONSTRUCTION_LIST = "reconstruction_list"
TAG_BROWSER_RECONSTRUCTION_DETAILS = "reconstruction_details"
TAG_BROWSER_FAMITRACKER_EXPORT = "famitracker_export"

# Messages
MSG_RECONSTRUCTION_INFO = "Reconstruction info"
MSG_RECONSTRUCTION_SELECT_AUDIO_FIRST = "Please select an audio file first"
MSG_CONFIG_ERROR = "Configuration error - please check settings"

# Template strings
TPL_RECONSTRUCTION_GEN_TAG = "gen_{}"

# File dialog settings
VAL_DIALOG_FILE_COUNT_SINGLE = 1

# Plot settings
VAL_PLOT_WIDTH_FULL = -1
VAL_PLOT_CHILDREN_SLOT = 2

# Waveform display settings
DIM_WAVEFORM_DEFAULT_HEIGHT = 300
CLR_WAVEFORM_LAYER_SAMPLE = (100, 200, 255, 255)
CLR_WAVEFORM_LAYER_RECONSTRUCTION = (100, 255, 100, 255)
VAL_WAVEFORM_SAMPLE_THICKNESS = 1.5
VAL_WAVEFORM_RECONSTRUCTION_THICKNESS = 1.2
VAL_WAVEFORM_ZOOM_FACTOR = 1.1
VAL_WAVEFORM_DEFAULT_Y_MIN = -1.0
VAL_WAVEFORM_DEFAULT_Y_MAX = 1.0
VAL_WAVEFORM_AXIS_SLOT = 1

# Waveform labels and messages
LBL_WAVEFORM_TIME_LABEL = "Time (samples)"
LBL_WAVEFORM_AMPLITUDE_LABEL = "Amplitude"
MSG_WAVEFORM_NO_FRAGMENT = "No fragment loaded. Select an instruction from the library tree to display its waveform."
LBL_WAVEFORM_SAMPLE_LAYER_NAME = "Sample"
LBL_WAVEFORM_RECONSTRUCTION_LAYER_NAME = "Reconstruction"
FMT_WAVEFORM_VALUE = "{}[{}] = {:.4f}"
FMT_WAVEFORM_FREQUENCY = "{:.2f} Hz"

# Button labels for waveform
LBL_WAVEFORM_BUTTON_RESET_X = "Reset X"
LBL_WAVEFORM_BUTTON_RESET_Y = "Reset Y"
LBL_WAVEFORM_BUTTON_RESET_ALL = "Reset All"
LBL_WAVEFORM_BUTTON_PLAY_AUDIO = "Play Audio"

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
DIM_PLAYER_PANEL_HEIGHT = 60
LBL_PLAYER_BUTTON_PLAY = "Play"
LBL_PLAYER_BUTTON_PAUSE = "Pause"
LBL_PLAYER_BUTTON_STOP = "Stop"
MSG_PLAYER_NO_AUDIO_LOADED = "No audio loaded"
MSG_PLAYER_AUDIO_PLAYBACK_ERROR = "Audio playback error"
TITLE_DIALOG_NO_AUDIO = "No Audio"
TITLE_DIALOG_PLAYBACK_ERROR = "Playback Error"

# Instruction panel constants
MSG_INSTRUCTION_DETAILS = "Instruction Details"
MSG_INSTRUCTION_NO_SELECTION = "No instruction selected"
LBL_INSTRUCTION_WAVEFORM = "Instruction Waveform"
LBL_INSTRUCTION_SPECTRUM = "Instruction Spectrum"

# Waveform layer colors
CLR_WAVEFORM_DEFAULT = (255, 255, 255, 255)
# layer colors also defined above (keep for compatibility)

# Waveform component suffixes
SUF_WAVEFORM_PLOT = "_plot"
SUF_WAVEFORM_X_AXIS = "_x_axis"
SUF_WAVEFORM_Y_AXIS = "_y_axis"
SUF_WAVEFORM_LEGEND = "_legend"
SUF_WAVEFORM_CONTROLS = "_controls"
SUF_WAVEFORM_INFO = "_info"


# Spectrum display settings
VAL_SPECTRUM_LOG_OFFSET = 1e-2
VAL_SPECTRUM_GRAYSCALE_MAX = 255
LBL_SPECTRUM_X_AXIS = "Frequency (Hz, log)"
LBL_SPECTRUM_Y_AXIS = "Energy"

DIM_WAVEFORM_DEFAULT_WIDTH = -1
DIM_WAVEFORM_DEFAULT_DISPLAY_HEIGHT = 300

# Boolean text values
LBL_GLOBAL_YES = "Yes"
LBL_GLOBAL_NO = "No"

# Default axis range
VAL_WAVEFORM_DEFAULT_X_MIN = 0.0
VAL_WAVEFORM_DEFAULT_X_MAX = 1.0

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

# Audio player default width
DIM_PLAYER_PANEL_DEFAULT_WIDTH = -1

# Audio player text constants
PFX_PLAYER_POSITION = "Position: "
SUF_PLAYER_SAMPLES = " samples"
LBL_BUTTON_OK = "OK"

# Instruction display text constants
PFX_INSTRUCTION_GENERATOR = "Generator: "
PFX_INSTRUCTION_NAME = "Instruction: "
PFX_INSTRUCTION_FREQUENCY = "Frequency: "
FMT_INSTRUCTION_FREQUENCY = "{:.2f} Hz"
MSG_INSTRUCTION_NO_FREQUENCY = "No frequency data"
PFX_INSTRUCTION_SAMPLE_LENGTH = "Sample Length: "
SUF_INSTRUCTION_SAMPLE_LENGTH = " samples"
PFX_INSTRUCTION_OFFSET = "Offset: "
LBL_INSTRUCTION_PARAMETERS_HEADER = "Instruction Parameters:"
PFX_INSTRUCTION_PARAMETER_INDENT = "  "
VAL_INSTRUCTION_FLOAT_PRECISION = 4
