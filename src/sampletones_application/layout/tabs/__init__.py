from pydantic import BaseModel

from sampletones_application.layout.tabs.instructions import InstructionsLayout
from sampletones_application.layout.tabs.main import MainLayout
from sampletones_application.layout.tabs.reconstruction import ReconstructionLayout
from sampletones_application.layout.tabs.sequencer import SequencerLayout


class TabsLayout(BaseModel, extra="forbid", frozen=True):
    main: MainLayout
    instructions: InstructionsLayout
    reconstruction: ReconstructionLayout
    sequencer: SequencerLayout
