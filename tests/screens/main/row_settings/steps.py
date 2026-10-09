from pathlib import Path
from typing import Dict, Tuple

from automation.screen import Screen
from automation.steps.main import home_path
from automation.worlds.home import HomeFile
from sampletones_core.constants.enums import ChannelName
from tests.screens.main.row_settings.constants import FREQUENCY, PAIR, PAIR_TAKES, PLAYED_SECONDS
from tests.suite.screens.seeds.constants import KICK, SNARE
from tests.suite.screens.seeds.recordings import Recording


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
