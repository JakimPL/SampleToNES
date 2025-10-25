# GUI Constants

# Window dimensions
MAIN_WINDOW_WIDTH = 1200
MAIN_WINDOW_HEIGHT = 800

# Layout dimensions
CONFIG_PANEL_WIDTH = 300
CONFIG_PANEL_HEIGHT = 280
LIBRARY_PANEL_HEIGHT = 200
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
MIN_SAMPLE_RATE = 8000
MAX_SAMPLE_RATE = 192000
MIN_CHANGE_RATE = 1
MAX_CHANGE_RATE = 1000
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

# File extensions
EXT_JSON = "*.json"
EXT_WAV = "*.wav"

# Default display values
DEFAULT_LIBRARY_DIR_DISPLAY = "Default: {}"
CUSTOM_LIBRARY_DIR_DISPLAY = "Custom: {}"
ERROR_PREFIX = "Error: {}"
LOADED_PREFIX = "Loaded: {}"
