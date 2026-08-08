from pydantic import BaseModel

from sampletones_application.layout.settings.audio import AudioSettingsLayout
from sampletones_application.layout.settings.display import DisplaySettingsLayout


class SettingsLayout(BaseModel, extra="forbid", frozen=True):
    """The geometry every settings dialog draws with.

    The label and combo columns are shared, so a field reads the same width in whichever dialog
    it appears; each dialog then states the size of its own windows.
    """

    combo_width: int
    label_width: int
    audio: AudioSettingsLayout
    display: DisplaySettingsLayout
