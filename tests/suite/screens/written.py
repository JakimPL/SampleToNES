from sampletones_application.config.managers.application import ApplicationConfigManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.state import ApplicationStateManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_core.configs import Config
from sampletones_shared.paths.user import CONFIG_PATH


def written_state() -> ApplicationState:
    """The session the application left in its home, read by the manager that restores it at the next start."""
    return ApplicationStateManager(UserProfile.user().state).state


def written_application_config() -> ApplicationConfig:
    """The application settings left in the home, read by the manager the next start reads them with."""
    return ApplicationConfigManager(UserProfile.user().config).config


def written_config() -> Config:
    """The reconstruction settings left in the documents folder, read by the manager the next start reads them with."""
    return ConfigManager(CONFIG_PATH).config
