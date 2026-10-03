from typing import Final

import pytest

from tests.suite.screens.dearpygui.display import VirtualDisplay

DISPLAY_KEY: Final[pytest.StashKey[VirtualDisplay]] = pytest.StashKey()
