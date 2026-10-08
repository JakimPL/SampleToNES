from pathlib import Path
from typing import Final

import pytest

from automation.dearpygui.display import VirtualDisplay

DISPLAY_KEY: Final[pytest.StashKey[VirtualDisplay]] = pytest.StashKey()
HOMES_KEY: Final[pytest.StashKey[Path]] = pytest.StashKey()
