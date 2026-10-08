import json
from pathlib import Path
from typing import Final

import pytest
import yaml

from automation.screen import Screen
from automation.worlds.home import World, screen_filling_state
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.state.current import Current
from sampletones_application.paths import APPLICATION_STATE_PATH
from sampletones_core.configs import Config
from sampletones_shared.paths.user import CONFIG_PATH
from tests.suite.screens.seeds.archives import WrittenBytes
from tests.suite.screens.seeds.recordings import Recording

RECORDING_SECONDS: Final[float] = 0.5
RECORDING_FREQUENCY: Final[float] = 220.0
UNKNOWN_CARD: Final[str] = "main.retired.panel"
GONE_FOLDER: Final[str] = "Gone"
LIBRARIES_FOLDER: Final[str] = "Libraries"
VIEWPORT_FIELD: Final[str] = "viewport"
WIDTH_FIELD: Final[str] = "width"
WRONG_KIND_OF_WIDTH: Final[str] = "wide"
GENERAL_FIELD: Final[str] = "general"
MISSING_SETTING: Final[str] = "max_workers"


def state_from_elsewhere() -> bytes:
    """A session another build left: it names a card and a folder this home lacks, and a width in words."""
    state = screen_filling_state().model_copy(
        update={
            "advanced_settings": True,
            "current": Current(tab=Tab.SEQUENCER),
            "collapsed_cards": {UNKNOWN_CARD: True},
            "expanded_directories": [Path.cwd() / GONE_FOLDER],
        }
    )
    document = state.model_dump(mode="json")
    document[VIEWPORT_FIELD][WIDTH_FIELD] = WRONG_KIND_OF_WIDTH
    return yaml.safe_dump(document).encode()


def config_from_elsewhere() -> bytes:
    """Reconstruction settings another build left: they name a library folder and lack a setting."""
    config = Config()
    general = config.general.model_copy(update={"library_directory": str(Path.cwd() / LIBRARIES_FOLDER)})
    document = config.model_copy(update={"general": general}).model_dump(mode="json")
    del document[GENERAL_FIELD][MISSING_SETTING]
    return json.dumps(document).encode()


class TestSessionFilesFromElsewhere:
    """A session naming what this home lacks, with a setting of the wrong kind, beside settings missing one.

    The application starts quietly and applies every setting the files give in a form this build reads: the
    Sequencer tab is in front, Advanced settings is shown, and the library folder is the one the settings
    name.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the foreign session, the foreign settings and a recording in the named library
        folder.
        """
        return World(
            state=None,
            application_config=None,
            config=None,
            files=(
                WrittenBytes(APPLICATION_STATE_PATH, state_from_elsewhere()),
                WrittenBytes(CONFIG_PATH, config_from_elsewhere()),
                Recording(Path.cwd() / LIBRARIES_FOLDER / "kick.wav", RECORDING_SECONDS, RECORDING_FREQUENCY),
            ),
        )

    def test_it_starts_without_a_word_and_applies_what_it_reads(self, screen: Screen) -> None:
        """No window shows, and the readable settings apply."""
        screen.expect(screen.tabs.front, Tab.SEQUENCER.__eq__, description="the Sequencer tab in front")

        assert screen.shown_windows() == ()
        assert screen.main.advanced.is_shown()
        assert screen.main.library_directory() == str(Path.cwd() / LIBRARIES_FOLDER)
