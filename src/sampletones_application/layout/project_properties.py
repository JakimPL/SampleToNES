from pydantic import BaseModel

from sampletones_application.layout.settings import SettingsWindowLayout


class ProjectPropertiesLayout(BaseModel, extra="forbid", frozen=True):
    window: SettingsWindowLayout
    label_width: int
    input_width: int
    comment_height: int
