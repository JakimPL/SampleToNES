TAG_PANEL_MAIN = "panel_main"
TAG_PANEL_MAIN_SETTINGS = "panel_main_settings"
TAG_PANEL_MAIN_CONFIG_CELL = "panel_main_config_cell"
TAG_PANEL_MAIN_RECONSTRUCTOR_CELL = "panel_main_reconstructor_cell"
TAG_TREE_MAIN_EXPLORER = "tree_main_explorer"
TAG_PANEL_MAIN_EXPLORER = "panel_main_explorer"
TAG_WINDOW_MAIN_EXPLORER_TREE = "window_main_explorer_tree"
TAG_GROUP_MAIN_EXPLORER_TREE = "group_main_explorer_tree"
TAG_GROUP_MAIN_EXPLORER_CONTROLS = "group_main_explorer_controls"
TAG_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING = "dialog_main_explorer_converter_running"
TAG_BUTTON_MAIN_EXPLORER_REFRESH = "button_main_explorer_refresh"
TAG_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL = "button_main_explorer_collapse_all"
TAG_PANEL_MAIN_CONFIG = "panel_main_config"
TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE = "checkbox_main_config_normalize"
TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE = "checkbox_main_config_quantize"
TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE = "input_main_config_sample_rate"
TAG_INPUT_MAIN_CONFIG_CHANGE_RATE = "input_main_config_change_rate"
TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA = "input_main_config_transformation_gamma"
TAG_PANEL_MAIN_RECONSTRUCTOR = "panel_main_reconstructor"
TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER = "slider_main_reconstructor_mixer"
TAG_PANEL_MAIN_ADVANCED = "panel_main_advanced"
TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS = "input_main_advanced_max_workers"
TAG_GROUP_MAIN_ADVANCED_LIBRARY_DIRECTORY = "group_main_advanced_library_directory"
TAG_PATH_MAIN_ADVANCED_LIBRARY_DIRECTORY_DISPLAY = "path_main_advanced_library_directory_display"
TAG_GROUP_MAIN_ADVANCED_OUTPUT_DIRECTORY = "group_main_advanced_output_directory"
TAG_PATH_MAIN_ADVANCED_OUTPUT_DIRECTORY_DISPLAY = "path_main_advanced_output_directory_display"
TAG_BUTTON_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY = "button_main_advanced_select_library_directory"
TAG_BUTTON_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY = "button_main_advanced_select_output_directory"
TAG_PROGRESS_MAIN_CONVERTER = "progress_main_converter"
TAG_TEXT_MAIN_CONVERTER_STATUS = "text_main_converter_status"
TAG_PANEL_MAIN_CONVERTER = "panel_main_converter"
TAG_GROUP_MAIN_CONVERTER = "group_main_converter"
TAG_PATH_MAIN_CONVERTER_INPUT_PATH = "path_main_converter_input_path"
TAG_TEXT_MAIN_CONVERTER_OUTPUT_PATH = "text_main_converter_output_path"
TAG_BUTTON_MAIN_CONVERTER_LOAD = "button_main_converter_load"
TAG_BUTTON_MAIN_CONVERTER_CANCEL = "button_main_converter_cancel"
TAG_DIALOG_MAIN_CONVERTER_SUCCESS = "dialog_main_converter_success"
TAG_BUTTON_MAIN_CONVERTER_CONVERT = "button_main_converter_convert"

SUF_MAIN_EXPLORER_NODE_DUMMY = "_node_dummy"

LBL_SECTION_MAIN_EXPLORER = "Filesystem"
LBL_BUTTON_MAIN_EXPLORER_REFRESH = "Refresh"
LBL_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL = "Collapse all"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_RECONSTRUCTION = "Load reconstruction"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_LIBRARY = "Load instructions library"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_FILE = "Reconstruct file"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_DIRECTORY = "Reconstruct directory"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_SET_AS_LIBRARY_DIRECTORY = "Set as instructions library directory"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_SET_AS_OUTPUT_DIRECTORY = "Set as output directory"
LBL_SECTION_MAIN_CONFIG = "General settings"
LBL_SECTION_MAIN_CONFIG_LIBRARY_SETTINGS = "Instructions library settings"
LBL_CHECKBOX_MAIN_CONFIG_NORMALIZE_AUDIO = "Normalize audio"
LBL_CHECKBOX_MAIN_CONFIG_QUANTIZE_AUDIO = "Quantize audio"
LBL_INPUT_MAIN_CONFIG_SAMPLE_RATE = "Sample rate"
LBL_INPUT_MAIN_CONFIG_CHANGE_RATE = "NES frequency"
LBL_SLIDER_MAIN_CONFIG_TRANSFORMATION_GAMMA = "FFT transformation"
LBL_TOOLTIP_MAIN_CONFIG_NORMALIZE = "Normalize audio to ensure consistent volume levels."
LBL_TOOLTIP_MAIN_CONFIG_QUANTIZE = "Quantize audio samples to 5-bit resolution."
LBL_TOOLTIP_MAIN_CONFIG_SAMPLE_RATE = "Set the sample rate (in Hz) for audio processing."
LBL_TOOLTIP_MAIN_CONFIG_CHANGE_RATE = (
    "Set the NES refresh rate (in Hz) for audio processing. NTSC = 60 Hz, PAL = 50 Hz."
)
LBL_TOOLTIP_MAIN_TRANSFORMATION_GAMMA = (
    "Interpolate between linear spectral features (0) features and logarithmic ones (100)."
)
LBL_SECTION_MAIN_RECONSTRUCTOR = "Generators"
LBL_SECTION_MAIN_RECONSTRUCTOR_SETTINGS = "Reconstructor settings"
LBL_SLIDER_MAIN_RECONSTRUCTOR_MIXER = "Mixer volume"
LBL_TOOLTIP_MAIN_RECONSTRUCTOR_MIXER = (
    "Amplify the NES generated audio. Lower values introduce compression, while higher values increase dynamics."
)
LBL_SECTION_MAIN_ADVANCED = "Advanced settings"
LBL_BUTTON_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY = "Select output directory"
LBL_BUTTON_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY = "Select instructions data directory"
LBL_INPUT_MAIN_ADVANCED_MAX_WORKERS = "Workers"
LBL_TOOLTIP_MAIN_ADVANCED_MAX_WORKERS = "Set the number parallel workers for audio processing tasks."
LBL_SECTION_MAIN_CONVERTER = "Converter"
LBL_BUTTON_MAIN_CONVERTER_CLOSE = "Close"
LBL_BUTTON_MAIN_CONVERTER_CANCEL = "Cancel"
LBL_BUTTON_MAIN_CONVERTER_LOAD = "Load"
LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE = "Convert sample"
LBL_BUTTON_MAIN_CONVERTER_CONVERT_DIRECTORY = "Convert directory"
LBL_MAIN_EXPLORER_NODE_DUMMY = "loading..."

MSG_MAIN_EXPLORER_CONVERTER_RUNNING = (
    "A conversion is already running. Please wait for it to complete or cancel the current operation "
    "before starting a new one."
)
MSG_MAIN_CONVERTER_ERROR = "Reconstruction failed."
MSG_MAIN_CONVERTER_SUCCESS = "Reconstruction completed successfully!"
MSG_MAIN_CONVERTER_CONFIG_NOT_AVAILABLE = "Configuration not available"
MSG_MAIN_CONVERTER_RECONSTRUCTION_COMPLETED = "Reconstruction completed!"
MSG_MAIN_CONVERTER_NO_FILES_TO_PROCESS = "No WAV files found to process."
MSG_MAIN_CONVERTER_IDLE = "No tasks in progress."
MSG_MAIN_CONVERTER_WAITING = "Waiting to start..."
MSG_MAIN_CONVERTER_GENERATING_LIBRARY = "Generating instructions library... (this may take a while)"
MSG_MAIN_CONVERTER_CANCELLING = "Aborting the conversion..."
MSG_MAIN_CONVERTER_CANCELLED = "Conversion cancelled."
MSG_MAIN_CONVERTER_INPUT = "Input:"
MSG_MAIN_CONVERTER_OUTPUT = "Output:"
MSG_STATUS_NODE_MAIN_EXPLORER_AUDIO_NO_AUTOPLAY = "Double-click to reconstruct audio. Right-click to open context menu."
MSG_STATUS_NODE_MAIN_EXPLORER_AUDIO = f"Click to play audio. {MSG_STATUS_NODE_MAIN_EXPLORER_AUDIO_NO_AUTOPLAY}"
MSG_STATUS_NODE_MAIN_EXPLORER_LIBRARY = "Double-click to open instructions library. Right-click to open context menu."

TTL_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING = "Conversion in progress"
TTL_DIALOG_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY = "Select library directory"
TTL_DIALOG_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY = "Select output directory"
TTL_DIALOG_MAIN_CONVERTER_PROGRESS = "Reconstruction progress"

TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR = "gen_{}"
TPL_MAIN_CONVERTER_PROGRESS = "Progress: {}/{} files"
TPL_RECONSTRUCTION_COMPLETE = "Reconstruction complete. Total error: {:.4f}"

DIM_PANEL_WIDTH_MAIN_EXPLORER = 440
DIM_PANEL_HEIGHT_MAIN_EXPLORER = -1
DIM_PANEL_HEIGHT_MAIN_CONFIG = 244
DIM_PANEL_HEIGHT_MAIN_CONVERTER = 252
DIM_BUTTON_WIDTH_MAIN_CONVERTER = -1
DIM_BUTTON_HEIGHT_MAIN_CONVERTER = 45
DIM_PANEL_HEIGHT_MAIN_ADVANCED = 148

VAL_RANGE_MAIN_ADVANCED_MAX_WORKERS = 1
VAL_FPS_TIME_INTERVAL = 2.0
VAL_PRIORITY_MAIN_EXPLORER_ADD_HANDLER = 8
VAL_PRIORITY_MAIN_EXPLORER_ADD_NODE = 7
