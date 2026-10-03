from sampletones_core.configs import Config
from tests.suite.screens.seeds.libraries import MiniLibrary
from tests.suite.screens.worlds.home import World, screen_filling_state


def library_world(config: Config, *, built: bool) -> World:
    """A world with Advanced settings on and ``config`` in force; with ``built`` set, the home also holds
    the library that ``config`` describes.
    """
    state = screen_filling_state().model_copy(update={"advanced_settings": True})
    return World(
        state=state,
        application_config=None,
        config=config,
        files=(MiniLibrary(config),) if built else (),
    )
