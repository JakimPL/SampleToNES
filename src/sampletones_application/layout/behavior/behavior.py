from pydantic import BaseModel

from sampletones_application.layout.behavior.display import DisplayBehavior
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.layout.behavior.ui import UIBehavior


class BehaviorConfig(BaseModel, extra="forbid", frozen=True):
    scheduling: SchedulingBehavior
    ui: UIBehavior
    display: DisplayBehavior
