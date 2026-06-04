from sampletones_application.text.hierarchy import Page, Panel, Widget
from sampletones_application.text.key import TagName

TAG_WINDOW_SETTINGS_AUDIO = TagName(Page.SETTINGS, Panel.AUDIO, Widget.WINDOW, "audio")
TAG_COMBO_SETTINGS_AUDIO_DEVICE = TagName(Page.SETTINGS, Panel.AUDIO, Widget.COMBO, "device")
TAG_COMBO_SETTINGS_AUDIO_SAMPLE_RATE = TagName(Page.SETTINGS, Panel.AUDIO, Widget.COMBO, "sample_rate")
TAG_COMBO_SETTINGS_AUDIO_BUFFER_SIZE = TagName(Page.SETTINGS, Panel.AUDIO, Widget.COMBO, "buffer_size")
TAG_GROUP_SETTINGS_AUDIO_DEVICE = TagName(Page.SETTINGS, Panel.AUDIO, Widget.GROUP, "device")
TAG_GROUP_SETTINGS_AUDIO_SAMPLE_RATE = TagName(Page.SETTINGS, Panel.AUDIO, Widget.GROUP, "sample_rate")
TAG_GROUP_SETTINGS_AUDIO_BUFFER_SIZE = TagName(Page.SETTINGS, Panel.AUDIO, Widget.GROUP, "buffer_size")
TAG_BUTTON_SETTINGS_AUDIO_APPLY = TagName(Page.SETTINGS, Panel.AUDIO, Widget.BUTTON, "apply")
TAG_BUTTON_SETTINGS_AUDIO_REFRESH = TagName(Page.SETTINGS, Panel.AUDIO, Widget.BUTTON, "refresh")

SUF_SETTINGS_AUDIO_HZ = " Hz"
SUF_SETTINGS_AUDIO_BIT = "-bit"
