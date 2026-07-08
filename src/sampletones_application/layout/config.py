from pydantic import BaseModel

from sampletones_application.layout.behavior import BehaviorConfig
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.glyphs import Glyphs
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.layout.instructions import InstructionsLayout
from sampletones_application.layout.main import MainLayout
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.project_properties import ProjectPropertiesLayout
from sampletones_application.layout.reconstructions import ReconstructionsLayout
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.layout.settings import SettingsLayout


class LayoutConfig(BaseModel, frozen=True):
    general: GeneralLayout
    glyphs: Glyphs
    graphs: GraphsLayout
    instructions: InstructionsLayout
    main: MainLayout
    player: PlayerLayout
    project_properties: ProjectPropertiesLayout
    reconstructions: ReconstructionsLayout
    sequencer: SequencerLayout
    settings: SettingsLayout
    behavior: BehaviorConfig
