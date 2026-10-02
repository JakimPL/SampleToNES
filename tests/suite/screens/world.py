from dataclasses import dataclass
from typing import Optional, Protocol, Tuple

from sampletones_application.config.managers.application import ApplicationConfigManager
from sampletones_application.config.managers.state import ApplicationStateManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.config.session.state.window import ViewportState
from sampletones_core.configs import Config
from sampletones_shared.paths.user import CONFIG_PATH
from tests.suite.screens.environment import SCREEN_SIZE
from tests.suite.screens.seeds import MiniLibrary


class HomeFile(Protocol):
    """Something a scenario's home holds before the application starts: a recording, a document, a library."""

    def write(self) -> None:
        """Writes it under the home of the scenario's process."""


@dataclass(frozen=True)
class World:
    """What a scenario's home holds before the application draws its first frame.

    Each file is written by the same model and the same manager the application reads it with, so
    a home seeded here is a home a previous run could have left.

    Attributes:
        state: The session the application restores, or ``None`` for a home no run has left one in.
        application_config: The application's settings, or ``None`` for a home holding none.
        config: The reconstruction settings in the documents folder, or ``None`` for a home holding none.
        files: Everything else the home holds.
    """

    state: Optional[ApplicationState]
    application_config: Optional[ApplicationConfig]
    config: Optional[Config]
    files: Tuple[HomeFile, ...]

    def write(self, profile: UserProfile) -> None:
        """Lays the world out in the home ``profile`` reads its settings from."""
        if self.state is not None:
            state_manager = ApplicationStateManager(profile.state)
            state_manager.state = self.state
            state_manager.save()

        if self.application_config is not None:
            config_manager = ApplicationConfigManager(profile.config)
            config_manager.config = self.application_config
            config_manager.save()

        if self.config is not None:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.config.save(CONFIG_PATH)

        for file in self.files:
            file.write()


def screen_filling_state() -> ApplicationState:
    """A session whose window spans the scenario's screen, which the application fits within its margins."""
    return ApplicationState(
        viewport=ViewportState(
            width=SCREEN_SIZE.width,
            height=SCREEN_SIZE.height,
            x=0,
            y=0,
        )
    )


def one_worker_config() -> Config:
    """Reconstruction settings running one job at a time, which keeps a scenario's run on a worker of its own."""
    config = Config()
    general = config.general.model_copy(update={"max_workers": 1})
    return config.model_copy(update={"general": general})


def converting_world(files: Tuple[HomeFile, ...]) -> World:
    """A home ready to convert: one-worker settings, a small library built for them, and ``files``."""
    config = one_worker_config()
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=config,
        files=(MiniLibrary(config), *files),
    )


def lived_in_world() -> World:
    """The home of a user who ran the application once: a session left behind, and nothing else."""
    return World(
        state=screen_filling_state(),
        application_config=None,
        config=None,
        files=(),
    )
