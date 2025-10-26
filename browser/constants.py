# GUI Constants

# Window dimensions
MAIN_WINDOW_WIDTH = 1200
MAIN_WINDOW_HEIGHT = 800

# Layout dimensions
CONFIG_PANEL_WIDTH = 300
CONFIG_PANEL_HEIGHT = 280
LIBRARY_PANEL_WIDTH = 300
LIBRARY_PANEL_HEIGHT = 400
RECONSTRUCTION_PANEL_WIDTH = 300
RECONSTRUCTION_PANEL_HEIGHT = 600
BROWSER_PANEL_WIDTH = 300
BROWSER_PANEL_HEIGHT = 600

# File dialog dimensions
FILE_DIALOG_WIDTH = 600
FILE_DIALOG_HEIGHT = 400

# Plot dimensions
WAVEFORM_PLOT_HEIGHT = 200

# Input validation ranges
MIN_WORKERS = 1

# Multiline text heights
FAMITRACKER_EXPORT_HEIGHT = 200

# GUI Labels
WINDOW_TITLE = "SampleToNES Converter"

# Menu labels
MENU_FILE = "File"
MENU_LOAD_CONFIG = "Load configuration"
MENU_LOAD_AUDIO = "Load audio"
MENU_LOAD_RECONSTRUCTION = "Load reconstruction"
MENU_EXIT = "Exit"

# Tab labels
TAB_CONFIGURATION = "Configuration"
TAB_RECONSTRUCTION = "Reconstruction"
TAB_BROWSER = "Browse results"

# Section headers
SECTION_GENERAL_SETTINGS = "General settings"
SECTION_LIBRARY_DIRECTORY = "Library directory"
SECTION_LIBRARY_SETTINGS = "Library settings"
SECTION_LIBRARY_PANEL = "Library"
SECTION_AUDIO_INPUT = "Audio input"
SECTION_GENERATOR_SELECTION = "Generator selection"
SECTION_WAVEFORM_DISPLAY = "Waveform display"
SECTION_SAVED_RECONSTRUCTIONS = "Saved reconstructions"
SECTION_RECONSTRUCTION_DETAILS = "Reconstruction details"
SECTION_FAMITRACKER_EXPORT = "FamiTracker export"

# Button labels
BUTTON_SELECT_LIBRARY_DIR = "Select library directory"
BUTTON_GENERATE_LIBRARY = "Generate library"
BUTTON_REGENERATE_LIBRARY = "Regenerate library"
BUTTON_REFRESH_LIBRARIES = "Refresh libraries"
BUTTON_SELECT_AUDIO_FILE = "Select audio file"
BUTTON_START_RECONSTRUCTION = "Start reconstruction"
BUTTON_PLAY_ORIGINAL = "Play original"
BUTTON_PLAY_RECONSTRUCTION = "Play reconstruction"
BUTTON_EXPORT_WAV = "Export WAV"
BUTTON_REFRESH_LIST = "Refresh list"

# Checkbox labels
CHECKBOX_NORMALIZE_AUDIO = "Normalize audio"
CHECKBOX_QUANTIZE_AUDIO = "Quantize audio"
CHECKBOX_TRIANGLE = "Triangle"
CHECKBOX_PULSE_1 = "Pulse 1"
CHECKBOX_PULSE_2 = "Pulse 2"
CHECKBOX_NOISE = "Noise"

# Input field labels
INPUT_MAX_WORKERS = "Max workers"
INPUT_SAMPLE_RATE = "Sample rate"
INPUT_CHANGE_RATE = "Change rate"

# Dialog titles
DIALOG_LOAD_CONFIG = "Load configuration"
DIALOG_LOAD_AUDIO = "Load audio"
DIALOG_LOAD_RECONSTRUCTION = "Load reconstruction"
DIALOG_SELECT_LIBRARY_DIR = "Select library directory"
DIALOG_EXPORT_WAV = "Export WAV"

# Plot labels
PLOT_AUDIO_WAVEFORMS = "Audio waveforms"
PLOT_TIME_SAMPLES = "Time (samples)"
PLOT_AMPLITUDE = "Amplitude"
PLOT_ORIGINAL = "Original"
PLOT_RECONSTRUCTION = "Reconstruction"

# Status messages
MSG_CONFIG_PREVIEW_DEFAULT = "Load or modify configuration to see preview"
MSG_NO_FILE_SELECTED = "No file selected"
MSG_NO_DIR_SELECTED = "No directory selected"
MSG_SELECT_RECONSTRUCTION = "Select a reconstruction to view details"
MSG_CONFIG_APPLIED = "Configuration applied successfully"
MSG_RECONSTRUCTION_COMPLETE = "Reconstruction complete. Total error: {:.4f}"
MSG_SELECT_AUDIO_AND_CONFIG = "Please select audio file and apply configuration first"
MSG_LIBRARY_EXISTS = "Library exists"
MSG_LIBRARY_NOT_EXISTS = "Library does not exist"
MSG_GENERATING_LIBRARY = "Generating library..."
MSG_LIBRARY_GENERATED = "Library generated successfully"
MSG_LIBRARY_NOT_LOADED = "Library is not loaded"
MSG_LIBRARY_LOADING = "Library is loading..."
MSG_CONFIGURATION_NOT_READY = "Configuration not ready"
MSG_CONFIGURATION_PREVIEW = "Configuration preview"
MSG_LIBRARIES = "Libraries"
MSG_AVAILABLE_LIBRARIES = "Libraries"
MSG_LIBRARY_NOT_EXISTS = "Library {} does not exist."
MSG_NO_VALID_INSTRUCTIONS = "No valid instructions found"
MSG_WINDOW_NOT_AVAILABLE = "Window not available"
MSG_ERROR_GENERATING_LIBRARY = "generating library"

# File extensions
EXT_JSON = "*.json"
EXT_WAV = "*.wav"

# Default display values
DEFAULT_LIBRARY_DIR_DISPLAY = "Default: {}"
CUSTOM_LIBRARY_DIR_DISPLAY = "Custom: {}"
ERROR_PREFIX = "Error: {}"
LOADED_PREFIX = "Loaded: {}"

# Template strings
TEMPLATE_LIBRARY_EXISTS = "Library {} exists."
TEMPLATE_LIBRARY_TAG = "lib_{}"
TEMPLATE_GENERATOR_TAG = "generator_{}_{}"
TEMPLATE_GROUP_TAG = "{}_{}_{}"
TEMPLATE_GROUP_LABEL = "{} ({} item(s))"

# GUI element tags
TAG_LIBRARY_PANEL = "library_panel"
TAG_LIBRARY_STATUS = "library_status"
TAG_LIBRARY_CONTROLS_GROUP = "library_controls_group"
TAG_GENERATE_LIBRARY_BUTTON = "generate_library_button"
TAG_LIBRARY_PROGRESS = "library_progress"
TAG_LIBRARY_DIRECTORY_DISPLAY = "library_directory_display"
TAG_CONFIG_PREVIEW = "config_preview"
TAG_NORMALIZE = "normalize"
TAG_QUANTIZE = "quantize"
TAG_MAX_WORKERS = "max_workers"
TAG_SAMPLE_RATE = "sample_rate"
TAG_CHANGE_RATE = "change_rate"
TAG_LIBRARIES_TREE = "libraries_tree"

# Indices and offsets
INDEX_FIRST_SELECTION = 0
DEFAULT_SLOT_VALUE = 1
DEFAULT_FLOAT_VALUE = 0.0
PROGRESS_COMPLETE_VALUE = 1.0

# Dictionary keys
KEY_SELECTIONS = "selections"

# Main GUI tags
TAG_MAIN_WINDOW = "main_window"
TAG_LEFT_PANELS_GROUP = "left_panels_group"
TAG_CONFIG_PANEL_GROUP = "config_panel_group"
TAG_LIBRARY_PANEL_GROUP = "library_panel_group"
TAG_CONFIG_TAB = "config_tab"
TAG_SELECTED_AUDIO_FILE = "selected_audio_file"
TAG_RECONSTRUCTION_PROGRESS = "reconstruction_progress"
TAG_GEN_TRIANGLE = "gen_triangle"
TAG_GEN_PULSE1 = "gen_pulse1"
TAG_GEN_PULSE2 = "gen_pulse2"
TAG_GEN_NOISE = "gen_noise"
TAG_WAVEFORM_PLOT = "waveform_plot"
TAG_X_AXIS = "x_axis"
TAG_Y_AXIS = "y_axis"
TAG_RECONSTRUCTION_INFO = "reconstruction_info"
TAG_RECONSTRUCTION_LIST = "reconstruction_list"
TAG_RECONSTRUCTION_DETAILS = "reconstruction_details"
TAG_FAMITRACKER_EXPORT = "famitracker_export"

# Messages
MSG_RECONSTRUCTION_INFO = "Reconstruction info"
MSG_SELECT_AUDIO_FIRST = "Please select an audio file first"
MSG_CONFIG_ERROR = "Configuration error - please check settings"

# Template strings
TEMPLATE_RECONSTRUCTION_GEN_TAG = "gen_{}"

# File dialog settings
FILE_COUNT_SINGLE = 1

# Plot settings
PLOT_WIDTH_FULL = -1
PLOT_CHILDREN_SLOT = 2

# Waveform display settings
WAVEFORM_DEFAULT_HEIGHT = 300
WAVEFORM_SAMPLE_COLOR = (100, 200, 255, 255)
WAVEFORM_FEATURE_COLOR = (255, 150, 100, 255)
WAVEFORM_RECONSTRUCTION_COLOR = (100, 255, 100, 255)
WAVEFORM_FEATURE_SCALE = 0.5
WAVEFORM_SAMPLE_THICKNESS = 1.5
WAVEFORM_RECONSTRUCTION_THICKNESS = 1.2
WAVEFORM_ZOOM_FACTOR = 1.1
WAVEFORM_DEFAULT_Y_MIN = -1.0
WAVEFORM_DEFAULT_Y_MAX = 1.0
WAVEFORM_AXIS_SLOT = 1

# Waveform labels and messages
WAVEFORM_TIME_LABEL = "Time (samples)"
WAVEFORM_AMPLITUDE_LABEL = "Amplitude"
WAVEFORM_NO_FRAGMENT_MSG = "No fragment loaded. Select an instruction from the library tree to display its waveform."
WAVEFORM_HOVER_PREFIX = "Hover: "
WAVEFORM_SAMPLE_LAYER_NAME = "Sample"
WAVEFORM_RECONSTRUCTION_LAYER_NAME = "Reconstruction"
WAVEFORM_POSITION_FORMAT = "Position: ({:.2f}, {:.4f})"
WAVEFORM_VALUE_FORMAT = "{}[{}] = {:.4f}"
WAVEFORM_FREQUENCY_FORMAT = "{:.2f} Hz"

# Button labels for waveform
BUTTON_RESET_X = "Reset X"
BUTTON_RESET_Y = "Reset Y"
BUTTON_RESET_ALL = "Reset All"
BUTTON_PLAY_AUDIO = "Play Audio"

# Waveform info format strings
WAVEFORM_GENERATOR_PREFIX = "Generator: "
WAVEFORM_FREQUENCY_PREFIX = "Frequency: "
WAVEFORM_SAMPLE_LENGTH_PREFIX = "Sample Length: "
WAVEFORM_OFFSET_PREFIX = "Offset: "
WAVEFORM_PARAMETERS_HEADER = "Instruction Parameters:"
WAVEFORM_FEATURE_NAME_FORMAT = "Feature (freq: {:.1f}Hz)"

# Numeric constants for waveform
WAVEFORM_FREQUENCY_DECIMALS = 2
WAVEFORM_VALUE_DECIMALS = 4
WAVEFORM_POSITION_DECIMALS = 2

# Boolean values
CHECKBOX_DEFAULT_ENABLED = True
PRIMARY_WINDOW_ENABLED = True

# Empty label
LABEL_EMPTY = ""

# Audio player constants
PLAYER_PANEL_HEIGHT = 60
BUTTON_PLAY = "Play"
BUTTON_PAUSE = "Pause"
BUTTON_STOP = "Stop"
MSG_NO_AUDIO_LOADED = "No audio loaded"
MSG_AUDIO_PLAYBACK_ERROR = "Audio playback error"
DIALOG_NO_AUDIO_TITLE = "No Audio"
DIALOG_PLAYBACK_ERROR_TITLE = "Playback Error"

# Instruction panel constants
MSG_INSTRUCTION_DETAILS = "Instruction Details"
MSG_NO_INSTRUCTION_SELECTED = "No instruction selected"
LABEL_INSTRUCTION_WAVEFORM = "Instruction Waveform"

# Waveform layer colors
WAVEFORM_DEFAULT_COLOR = (255, 255, 255, 255)
WAVEFORM_LAYER_SAMPLE_COLOR = (100, 200, 255, 255)
WAVEFORM_LAYER_FEATURE_COLOR = (255, 150, 100, 255)
WAVEFORM_LAYER_RECONSTRUCTION_COLOR = (100, 255, 100, 255)
