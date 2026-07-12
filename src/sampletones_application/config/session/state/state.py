from pydantic import BaseModel, Field

from sampletones_application.config.session.state.current import Current
from sampletones_application.config.session.state.paths import LastPaths
from sampletones_application.config.session.state.window import ViewportState


class ApplicationState(BaseModel):
    viewport: ViewportState = Field(
        default_factory=ViewportState,
        description="The state of the main application window.",
    )
    advanced_settings: bool = Field(
        default=False,
        description="If advanced settings are shown in the config panel.",
    )
    current: Current = Field(
        default_factory=Current,
        description="The current state of application elements, e.g. selected tab.",
    )
    last_paths: LastPaths = Field(
        default_factory=LastPaths,
        description="The last used file system paths.",
    )
