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
TAG_SETTINGS_AUDIO_GROUP_DEVICE = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.GROUP,
    "device",
)
TAG_SETTINGS_AUDIO_GROUP_SAMPLE_RATE = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.GROUP,
    "sample_rate",
)
TAG_SETTINGS_AUDIO_GROUP_BUFFER_SIZE = TagName(
    Page.SETTINGS,
    Panel.AUDIO,
    Widget.GROUP,
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

FMT_SETTINGS_AUDIO_HZ = " Hz"
FMT_SETTINGS_AUDIO_BIT = "-bit"
