from pathlib import Path
from typing import Dict, Tuple

from sampletones_core.constants.enums import ChannelName
from tests.screens.main.row_settings.constants import FREQUENCY, PAIR, PAIR_TAKES, PLAYED_SECONDS
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import home_path
from tests.suite.screens.vocabulary.recordings import KICK, SNARE
from tests.suite.screens.worlds.home import HomeFile


def recordings() -> Tuple[HomeFile, ...]:
    """The recordings the home holds: kick, snare and the two takes in the Pair folder."""
    return (
        Recording(destination=home_path(KICK), seconds=PLAYED_SECONDS, frequency=FREQUENCY),
        Recording(destination=home_path(SNARE), seconds=PLAYED_SECONDS, frequency=FREQUENCY),
        *(
            Recording(destination=home_path(PAIR) / name, seconds=PLAYED_SECONDS, frequency=FREQUENCY)
            for name in PAIR_TAKES
        ),
    )


def ticked(screen: Screen, path: Path) -> Dict[ChannelName, bool]:
    """Reads which channel boxes the list shows ticked on the row at ``path``."""
    return {channel: screen.main.converter.list.channel_ticked(path, channel) for channel in ChannelName}
