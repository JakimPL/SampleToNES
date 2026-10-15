from pathlib import Path
from typing import Final, Optional

import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.logic.reconstruction.keys import KeyArming
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from tests.suite.headless import profile_in

SAMPLE_ROOT: Final[int] = 60
REFERENCE_PITCH: Final[int] = 60
REFERENCE_PERIOD: Final[int] = 8


class Tab:
    """The Reconstructions tab as the keys read it: the instrument in front of it, or none."""

    def __init__(self) -> None:
        self.instrument: Optional[Instrument] = None


def lead() -> Instrument:
    """An instrument holding a note while its key is down, its frames changing so a tick out of place shows."""
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 12, 9), loop_point=1),
            arpeggio=Envelope[int](items=(0, 4)),
            duty_cycle=Envelope[int](items=(2,)),
        ),
        initial_pitch=REFERENCE_PITCH,
        initial_period=REFERENCE_PERIOD,
    )


@pytest.fixture
def controller() -> ProjectController:
    controller = ProjectController(ProjectManager())
    controller.new()
    return controller


@pytest.fixture
def session(tmp_path: Path) -> SessionManager:
    return SessionManager(profile_in(tmp_path))


@pytest.fixture
def tab() -> Tab:
    return Tab()


@pytest.fixture
def audition(tab: Tab, controller: ProjectController) -> InstrumentAuditionLogic:
    return InstrumentAuditionLogic(tab, controller)


@pytest.fixture
def arming(
    tab: Tab,
    audition: InstrumentAuditionLogic,
    reconstruction_manager: ReconstructionManager,
    controller: ProjectController,
    session: SessionManager,
) -> KeyArming:
    return KeyArming(tab, audition, reconstruction_manager, controller, session, sample_root=SAMPLE_ROOT)


@pytest.fixture
def instrument(tab: Tab, controller: ProjectController) -> Instrument:
    """The project's instrument, put in front of the tab."""
    added = controller.add_instrument(lead())
    tab.instrument = added
    return added
