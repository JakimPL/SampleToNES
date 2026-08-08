from pydantic import BaseModel

from sampletones_application.layout.behavior.behavior import BehaviorConfig
from sampletones_application.layout.fonts import FontsLayout
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.glyphs.glyphs import Glyphs
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.project_properties import ProjectPropertiesLayout
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.layout.tabs import TabsLayout


class LayoutConfig(BaseModel, extra="forbid", frozen=True):
    general: GeneralLayout
    fonts: FontsLayout
    glyphs: Glyphs
    graphs: GraphsLayout
    tabs: TabsLayout
    player: PlayerLayout
    project_properties: ProjectPropertiesLayout
    settings: SettingsLayout
    behavior: BehaviorConfig
