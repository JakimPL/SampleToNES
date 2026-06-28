from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key import TagName

TAG_MAIN_PANEL = TagName(
    Page.MAIN,
    Panel.IMPLICIT,
    Widget.PANEL,
    "",
)
TAG_MAIN_PANEL_SETTINGS = TagName(
    Page.MAIN,
    Panel.IMPLICIT,
    Widget.PANEL,
    "settings",
)
TAG_MAIN_CONFIG_PANEL_CONFIG_CELL = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.PANEL,
    "config_cell",
)
TAG_MAIN_RECONSTRUCTOR_PANEL_RECONSTRUCTOR_CELL = TagName(
    Page.MAIN,
    Panel.RECONSTRUCTOR,
    Widget.PANEL,
    "reconstructor_cell",
)
TAG_MAIN_EXPLORER_TREE = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.TREE,
    "explorer",
)
TAG_MAIN_EXPLORER_PANEL = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.PANEL,
    "explorer",
)
TAG_MAIN_EXPLORER_WINDOW_TREE = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.WINDOW,
    "tree",
)
TAG_MAIN_EXPLORER_GROUP_TREE = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.GROUP,
    "tree",
)
TAG_MAIN_EXPLORER_GROUP_CONTROLS = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.GROUP,
    "controls",
)
TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.DIALOG,
    "converter_running",
)
TAG_MAIN_EXPLORER_BUTTON_REFRESH = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.BUTTON,
    "refresh",
)
TAG_MAIN_EXPLORER_BUTTON_COLLAPSE_ALL = TagName(
    Page.MAIN,
    Panel.EXPLORER,
    Widget.BUTTON,
    "collapse_all",
)
TAG_MAIN_CONFIG_PANEL = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.PANEL,
    "config",
)
TAG_MAIN_CONFIG_CHECKBOX_NORMALIZE = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.CHECKBOX,
    "normalize",
)
TAG_MAIN_CONFIG_CHECKBOX_QUANTIZE = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.CHECKBOX,
    "quantize",
)
TAG_MAIN_CONFIG_INPUT_SAMPLE_RATE = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.INPUT,
    "sample_rate",
)
TAG_MAIN_CONFIG_INPUT_NES_FREQUENCY = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.INPUT,
    "nes_frequency",
)
TAG_MAIN_CONFIG_COMBO_SPECTRUM_METHOD = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.COMBO,
    "spectrum_method",
)
TAG_MAIN_CONFIG_INPUT_TRANSFORMATION_GAMMA = TagName(
    Page.MAIN,
    Panel.CONFIG_PANEL,
    Widget.INPUT,
    "transformation_gamma",
)
TAG_MAIN_RECONSTRUCTOR_PANEL = TagName(
    Page.MAIN,
    Panel.RECONSTRUCTOR,
    Widget.PANEL,
    "reconstructor",
)
TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE = TagName(
    Page.MAIN,
    Panel.RECONSTRUCTOR,
    Widget.SLIDER,
    "drive",
)
TAG_MAIN_ADVANCED_PANEL = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.PANEL,
    "advanced",
)
TAG_MAIN_ADVANCED_INPUT_MAX_WORKERS = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.INPUT,
    "max_workers",
)
TAG_MAIN_ADVANCED_GROUP_LIBRARY_DIRECTORY = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.GROUP,
    "library_directory",
)
TAG_MAIN_ADVANCED_PATH_LIBRARY_DIRECTORY_DISPLAY = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.PATH,
    "library_directory_display",
)
TAG_MAIN_ADVANCED_GROUP_RECONSTRUCTIONS_DIRECTORY = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.GROUP,
    "reconstructions_directory",
)
TAG_MAIN_ADVANCED_PATH_OUTPUT_DIRECTORY_DISPLAY = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.PATH,
    "output_directory_display",
)
TAG_MAIN_ADVANCED_BUTTON_SELECT_LIBRARY_DIRECTORY = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.BUTTON,
    "select_library_directory",
)
TAG_MAIN_ADVANCED_BUTTON_SELECT_OUTPUT_DIRECTORY = TagName(
    Page.MAIN,
    Panel.ADVANCED,
    Widget.BUTTON,
    "select_output_directory",
)
TAG_MAIN_CONVERTER_PROGRESS = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.PROGRESS,
    "converter",
)
TAG_MAIN_CONVERTER_TEXT_STATUS = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.TEXT,
    "status",
)
TAG_MAIN_CONVERTER_PANEL = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.PANEL,
    "converter",
)
TAG_MAIN_CONVERTER_GROUP = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.GROUP,
    "converter",
)
TAG_MAIN_CONVERTER_PATH_INPUT_PATH = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.PATH,
    "input_path",
)
TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.TEXT,
    "output_path",
)
TAG_MAIN_CONVERTER_BUTTON_LOAD = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.BUTTON,
    "load",
)
TAG_MAIN_CONVERTER_BUTTON_CANCEL = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.BUTTON,
    "cancel",
)
TAG_MAIN_CONVERTER_DIALOG_SUCCESS = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.DIALOG,
    "success",
)
TAG_MAIN_CONVERTER_BUTTON_CONVERT = TagName(
    Page.MAIN,
    Panel.CONVERTER,
    Widget.BUTTON,
    "convert",
)

PRE_MAIN_RECONSTRUCTOR_GENERATOR = "gen."
SUF_MAIN_EXPLORER_NODE_DUMMY = ".node_dummy"
