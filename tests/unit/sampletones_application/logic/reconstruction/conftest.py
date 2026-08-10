import pytest

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from tests.suite.application import scheduling, synchronous_queue

__all__ = ["scheduling", "synchronous_queue"]


@pytest.fixture
def reconstruction_manager(scheduling: SchedulingBehavior) -> ReconstructionManager:
    return ReconstructionManager(scheduling=scheduling)
