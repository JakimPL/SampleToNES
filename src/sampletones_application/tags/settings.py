from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key.tag import TagName
from sampletones_application.tags.compose import compose_tag

TAG_SETTINGS_AUDIO_WINDOW = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.WINDOW,
    "audio",
)
TAG_SETTINGS_AUDIO_COMBO_DEVICE = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.COMBO,
    "device",
)
TAG_SETTINGS_AUDIO_COMBO_SAMPLE_RATE = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.COMBO,
    "sample_rate",
)
TAG_SETTINGS_AUDIO_COMBO_BUFFER_SIZE = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.COMBO,
    "buffer_size",
)
TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.SLIDER,
    "master_gain",
)
TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.TEXT,
    "master_gain_db",
)
TAG_SETTINGS_AUDIO_BUTTON_APPLY = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.BUTTON,
    "apply",
)
TAG_SETTINGS_AUDIO_BUTTON_REFRESH = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.BUTTON,
    "refresh",
)

TAG_SETTINGS_DISPLAY_WINDOW = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.WINDOW,
    "display",
)
TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.COMBO,
    "resolution",
)
TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.COMBO,
    "frame_rate",
)
TAG_SETTINGS_DISPLAY_COMBO_PALETTE = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.COMBO,
    "palette",
)
TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.CHECKBOX,
    "borderless",
)
TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.CHECKBOX,
    "fullscreen",
)
TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.CHECKBOX,
    "vsync",
)
TAG_SETTINGS_DISPLAY_BUTTON_OK = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.BUTTON,
    "ok",
)
TAG_SETTINGS_DISPLAY_BUTTON_CANCEL = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.BUTTON,
    "cancel",
)
TAG_SETTINGS_DISPLAY_DIALOG_DISCARD = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.DIALOG,
    "discard",
)

TAG_SETTINGS_DISPLAY_WINDOW_COUNTDOWN = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.WINDOW,
    "countdown",
)
TAG_SETTINGS_DISPLAY_TEXT_COUNTDOWN = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.TEXT,
    "countdown",
)
TAG_SETTINGS_DISPLAY_BUTTON_KEEP = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.BUTTON,
    "keep",
)
TAG_SETTINGS_DISPLAY_BUTTON_REVERT = TagName(
    Page.SETTINGS,
    Panel.DISPLAY,
    Widget.BUTTON,
    "revert",
)

TAG_SETTINGS_RENDER_WINDOW = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.WINDOW,
    "render",
)
TAG_SETTINGS_RENDER_GROUP_SETUP = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.GROUP,
    "setup",
)
TAG_SETTINGS_RENDER_GROUP_PROGRESS = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.GROUP,
    "progress",
)
TAG_SETTINGS_RENDER_GROUP_DEPTH = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.GROUP,
    "depth",
)
TAG_SETTINGS_RENDER_GROUP_BITRATE = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.GROUP,
    "bitrate",
)
TAG_SETTINGS_RENDER_GROUP_DESTINATION = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.GROUP,
    "destination",
)
TAG_SETTINGS_RENDER_COMBO_FORMAT = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.COMBO,
    "format",
)
TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.COMBO,
    "sample_rate",
)
TAG_SETTINGS_RENDER_COMBO_DEPTH = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.COMBO,
    "depth",
)
TAG_SETTINGS_RENDER_COMBO_BITRATE = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.COMBO,
    "bitrate",
)
TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.CHECKBOX,
    "normalize",
)
TAG_SETTINGS_RENDER_TEXT_DURATION = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.TEXT,
    "duration",
)
TAG_SETTINGS_RENDER_TEXT_STATUS = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.TEXT,
    "status",
)
TAG_SETTINGS_RENDER_PATH_DESTINATION = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.PATH,
    "destination",
)
TAG_SETTINGS_RENDER_PROGRESS = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.PROGRESS,
    "render",
)
TAG_SETTINGS_RENDER_BUTTON_BROWSE = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.BUTTON,
    "browse",
)
TAG_SETTINGS_RENDER_BUTTON_START = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.BUTTON,
    "start",
)
TAG_SETTINGS_RENDER_BUTTON_CLOSE = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.BUTTON,
    "close",
)
TAG_SETTINGS_RENDER_BUTTON_CANCEL = TagName(
    Page.SETTINGS,
    Panel.RENDER,
    Widget.BUTTON,
    "cancel",
)

TAG_SETTINGS_KEYBINDINGS_WINDOW = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.WINDOW,
    "keybindings",
)
TAG_SETTINGS_KEYBINDINGS_COMBO_SCHEME = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.COMBO,
    "scheme",
)
TAG_SETTINGS_KEYBINDINGS_INPUT_FILTER = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.INPUT,
    "filter",
)
TAG_SETTINGS_KEYBINDINGS_INPUT_SHORTCUT = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.INPUT,
    "shortcut",
)
TAG_SETTINGS_KEYBINDINGS_PANEL_ACTIONS = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.PANEL,
    "actions",
)
TAG_SETTINGS_KEYBINDINGS_TABLE_ACTIONS = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.TABLE,
    "actions",
)
TAG_SETTINGS_KEYBINDINGS_TEXT_MESSAGE = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.TEXT,
    "message",
)
TAG_SETTINGS_KEYBINDINGS_BUTTON_CLEAR = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.BUTTON,
    "clear",
)
TAG_SETTINGS_KEYBINDINGS_BUTTON_RESET = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.BUTTON,
    "reset",
)
TAG_SETTINGS_KEYBINDINGS_BUTTON_OK = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.BUTTON,
    "ok",
)
TAG_SETTINGS_KEYBINDINGS_BUTTON_CANCEL = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.BUTTON,
    "cancel",
)
TAG_SETTINGS_KEYBINDINGS_DIALOG_REASSIGN = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.DIALOG,
    "reassign",
)
TAG_SETTINGS_KEYBINDINGS_DIALOG_RESET = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.DIALOG,
    "reset",
)
TAG_SETTINGS_KEYBINDINGS_DIALOG_DISCARD = TagName(
    Page.SETTINGS,
    Panel.KEYBINDINGS,
    Widget.DIALOG,
    "discard",
)

PRE_SETTINGS_KEYBINDINGS_GROUP = compose_tag(TAG_SETTINGS_KEYBINDINGS_TABLE_ACTIONS, "group")
PRE_SETTINGS_KEYBINDINGS_ROW = compose_tag(TAG_SETTINGS_KEYBINDINGS_TABLE_ACTIONS, "row")
SUF_SETTINGS_KEYBINDINGS_ACTION = "action"
SUF_SETTINGS_KEYBINDINGS_SHORTCUT = "shortcut"

TAG_SETTINGS_PROPERTIES_WINDOW = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.WINDOW,
    "properties",
)
TAG_SETTINGS_PROPERTIES_INPUT_TITLE = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.INPUT,
    "title",
)
TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.INPUT,
    "author",
)
TAG_SETTINGS_PROPERTIES_INPUT_COMMENT = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.INPUT,
    "comment",
)
TAG_SETTINGS_PROPERTIES_INPUT_FIRST_HIGHLIGHT = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.INPUT,
    "first_highlight",
)
TAG_SETTINGS_PROPERTIES_INPUT_SECOND_HIGHLIGHT = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.INPUT,
    "second_highlight",
)
TAG_SETTINGS_PROPERTIES_BUTTON_OK = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.BUTTON,
    "ok",
)
TAG_SETTINGS_PROPERTIES_BUTTON_CANCEL = TagName(
    Page.SETTINGS,
    Panel.PROPERTIES,
    Widget.BUTTON,
    "cancel",
)
