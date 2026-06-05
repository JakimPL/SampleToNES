from sampletones_application.categories.abstract import AbstractElement


class ExplorerElements(AbstractElement):
    SECTION = "section"
    REFRESH_BUTTON = "refresh_button"
    COLLAPSE_ALL_BUTTON = "collapse_all_button"
    CONTEXT_LOAD_RECONSTRUCTION = "context_load_reconstruction"
    CONTEXT_LOAD_LIBRARY = "context_load_library"
    CONTEXT_RECONSTRUCT_FILE = "context_reconstruct_file"
    CONTEXT_RECONSTRUCT_DIRECTORY = "context_reconstruct_directory"
    CONTEXT_SET_LIBRARY_DIRECTORY = "context_set_library_directory"
    CONTEXT_SET_OUTPUT_DIRECTORY = "context_set_output_directory"
    NODE_DUMMY = "node_dummy"
    STATUS_NODE_AUDIO_NO_AUTOPLAY = "status_node_audio_no_autoplay"
    STATUS_NODE_AUDIO = "status_node_audio"
    STATUS_NODE_LIBRARY = "status_node_library"
    CONVERTER_RUNNING_MSG = "converter_running_msg"
    CONVERTER_RUNNING_DIALOG = "converter_running_dialog"


class ConfigPanelElements(AbstractElement):
    SECTION = "section"
    SECTION_LIBRARY = "section_library"
    CHECKBOX_NORMALIZE = "checkbox_normalize"
    CHECKBOX_QUANTIZE = "checkbox_quantize"
    INPUT_SAMPLE_RATE = "input_sample_rate"
    INPUT_CHANGE_RATE = "input_change_rate"
    SLIDER_TRANSFORMATION_GAMMA = "slider_transformation_gamma"
    TOOLTIP_NORMALIZE = "tooltip_normalize"
    TOOLTIP_QUANTIZE = "tooltip_quantize"
    TOOLTIP_SAMPLE_RATE = "tooltip_sample_rate"
    TOOLTIP_CHANGE_RATE = "tooltip_change_rate"
    TOOLTIP_TRANSFORMATION_GAMMA = "tooltip_transformation_gamma"


class ReconstructorElements(AbstractElement):
    SECTION_GENERATORS = "section_generators"
    SECTION_SETTINGS = "section_settings"
    SLIDER_MIXER = "slider_mixer"
    TOOLTIP_MIXER = "tooltip_mixer"


class ConverterElements(AbstractElement):
    SECTION = "section"
    CLOSE_BUTTON = "close_button"
    CANCEL_BUTTON = "cancel_button"
    LOAD_BUTTON = "load_button"
    CONVERT_SAMPLE_BUTTON = "convert_sample_button"
    CONVERT_DIRECTORY_BUTTON = "convert_directory_button"
    STATUS_ERROR = "status_error"
    STATUS_SUCCESS = "status_success"
    STATUS_CONFIG_NOT_AVAILABLE = "status_config_not_available"
    STATUS_RECONSTRUCTION_COMPLETED = "status_reconstruction_completed"
    STATUS_NO_FILES = "status_no_files"
    STATUS_IDLE = "status_idle"
    STATUS_WAITING = "status_waiting"
    STATUS_GENERATING_LIBRARY = "status_generating_library"
    STATUS_CANCELLING = "status_cancelling"
    STATUS_CANCELLED = "status_cancelled"
    STATUS_INPUT_LABEL = "status_input_label"
    STATUS_OUTPUT_LABEL = "status_output_label"
    PROGRESS_DIALOG = "progress_dialog"
    PROGRESS_TEMPLATE = "progress_template"
    COMPLETE_TEMPLATE = "complete_template"


class AdvancedElements(AbstractElement):
    SECTION = "section"
    SELECT_OUTPUT_DIRECTORY = "select_output_directory"
    SELECT_LIBRARY_DIRECTORY = "select_library_directory"
    INPUT_MAX_WORKERS = "input_max_workers"
    TOOLTIP_MAX_WORKERS = "tooltip_max_workers"
