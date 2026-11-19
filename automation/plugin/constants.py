from pathlib import Path
from typing import Final

import pytest

from automation.boundaries.sound_server import SoundServer
from automation.dearpygui.display import VirtualDisplay

DISPLAY_KEY: Final[pytest.StashKey[VirtualDisplay]] = pytest.StashKey()
HOMES_KEY: Final[pytest.StashKey[Path]] = pytest.StashKey()
SOUND_SERVER_KEY: Final[pytest.StashKey[SoundServer]] = pytest.StashKey()
