from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key import TagName

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
