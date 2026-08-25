from pydantic import BaseModel

from sampletones_application.layout.settings.audio import AudioSettingsLayout
from sampletones_application.layout.settings.display import DisplaySettingsLayout
from sampletones_application.layout.settings.export import ExportSettingsLayout
from sampletones_application.layout.settings.keybindings import KeybindingsSettingsLayout
from sampletones_application.layout.settings.render import RenderSettingsLayout


class SettingsLayout(BaseModel, extra="forbid", frozen=True):
    """The geometry every settings dialog draws with.

    The label and combo columns are shared, so a field reads the same width in whichever dialog
    it appears; each dialog then states the size of its own windows.
    """

    combo_width: int
    label_width: int
    audio: AudioSettingsLayout
    display: DisplaySettingsLayout
    keybindings: KeybindingsSettingsLayout
    render: RenderSettingsLayout
    export: ExportSettingsLayout
