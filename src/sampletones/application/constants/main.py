TAG_PANEL_MAIN = "main_panel"
TAG_PANEL_MAIN_SETTINGS = "main_panel_settings"
TAG_PANEL_MAIN_CONFIG_CELL = "main_panel_config_cell"
TAG_PANEL_MAIN_RECONSTRUCTOR_CELL = "main_panel_reconstructor_cell"
TAG_TREE_MAIN_EXPLORER = "explorer_tree"
TAG_PANEL_MAIN_EXPLORER = "explorer_panel"
TAG_WINDOW_MAIN_EXPLORER_TREE = "explorer_tree_window"
TAG_GROUP_MAIN_EXPLORER_TREE = "explorer_tree_group"
TAG_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING = "explorer_converter_running_info_dialog"
TAG_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL = "collapse_all"
TAG_PANEL_MAIN_CONFIG = "config_panel"
TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE = "normalize"
TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE = "quantize"
TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE = "sample_rate"
TAG_INPUT_MAIN_CONFIG_CHANGE_RATE = "change_rate"
TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA = "transformation_gamma"
TAG_PANEL_MAIN_RECONSTRUCTOR = "reconstructor_panel"
TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER = "mixer"
TAG_PANEL_MAIN_ADVANCED = "advanced_panel"
TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS = "max_workers"
TAG_GROUP_MAIN_ADVANCED_LIBRARY_DIRECTORY = "config_paths_instructions_group"
TAG_PATH_MAIN_ADVANCED_LIBRARY_DIRECTORY_DISPLAY = "library_directory_display"
TAG_GROUP_MAIN_ADVANCED_OUTPUT_DIRECTORY = "reconstructor_output_directory_group"
TAG_PATH_MAIN_ADVANCED_OUTPUT_DIRECTORY_DISPLAY = "output_directory_display"
TAG_BUTTON_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY = "config_library_directory"
TAG_BUTTON_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY = "reconstructor_select_output_directory_button"
TAG_PROGRESS_MAIN_CONVERTER = "converter_progress"
TAG_TEXT_MAIN_CONVERTER_STATUS = "converter_status"
TAG_PANEL_MAIN_CONVERTER = "converter_panel"
TAG_GROUP_MAIN_CONVERTER = "converter_subpanel"
TAG_PATH_MAIN_CONVERTER_INPUT_PATH = "converter_input_path_text"
TAG_TEXT_MAIN_CONVERTER_OUTPUT_PATH = "converter_output_path_text"
TAG_BUTTON_MAIN_CONVERTER_LOAD = "converter_load_button"
TAG_BUTTON_MAIN_CONVERTER_CANCEL = "converter_cancel_button"
TAG_DIALOG_MAIN_CONVERTER_SUCCESS = "converter_success_dialog"
TAG_BUTTON_MAIN_CONVERTER_CONVERT = "converter_convert_button"

SUF_MAIN_EXPLORER_NODE_HANDLER = "_node_handler"
SUF_MAIN_EXPLORER_NODE_DUMMY = "_node_dummy"

LBL_SECTION_MAIN_EXPLORER = "Filesystem"
LBL_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL = "Collapse all"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_RECONSTRUCTION = "Load reconstruction"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_LIBRARY = "Load instructions library"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_FILE = "Reconstruct file"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_DIRECTORY = "Reconstruct directory"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_MARK_AS_FAVORITE = "Mark as favorite"
LBL_CONTEXT_ITEM_MAIN_EXPLORER_UNMARK_AS_FAVORITE = "Unmark as favorite"
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
MSG_MAIN_CONVERTER_GENERATING_LIBRARY = "Generating instructions library..."
MSG_MAIN_CONVERTER_CANCELLING = "Aborting the conversion..."
MSG_MAIN_CONVERTER_CANCELLED = "Conversion cancelled."
MSG_MAIN_CONVERTER_INPUT = "Input:"
MSG_MAIN_CONVERTER_OUTPUT = "Output:"

TTL_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING = "Conversion in progress"
TTL_DIALOG_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY = "Select library directory"
TTL_DIALOG_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY = "Select output directory"
TTL_DIALOG_MAIN_CONVERTER_PROGRESS = "Reconstruction progress"

TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR = "gen_{}"
TPL_MAIN_CONVERTER_PROGRESS = "Progress: {}/{} files"
TPL_RECONSTRUCTION_COMPLETE = "Reconstruction complete. Total error: {:.4f}"

DIM_PANEL_WIDTH_MAIN_EXPLORER = 440
DIM_PANEL_HEIGHT_MAIN_EXPLORER = -1
DIM_PANEL_HEIGHT_MAIN_CONFIG = 258
DIM_PANEL_HEIGHT_MAIN_CONVERTER = 260
DIM_BUTTON_WIDTH_MAIN_CONVERTER = -1
DIM_BUTTON_HEIGHT_MAIN_CONVERTER = 45
DIM_PANEL_HEIGHT_MAIN_ADVANCED = 162

VAL_RANGE_MAIN_ADVANCED_MAX_WORKERS = 1
VAL_CHECKBOX_MAIN_RECONSTRUCTOR_ENABLED = True
