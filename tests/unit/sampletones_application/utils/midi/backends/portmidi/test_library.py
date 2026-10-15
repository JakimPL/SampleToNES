import subprocess
import sys
from typing import Final

import pytest

pytest.importorskip("pygame", reason="pygame-ce is installed on Windows and macOS alone")

IMPORT_SECONDS: Final[float] = 60.0
PROBE: Final[str] = """
import os
os.environ.pop("PYGAME_HIDE_SUPPORT_PROMPT", None)
from sampletones_application.utils.midi.backends.portmidi import load_portmidi
library = load_portmidi()
library.CountDevices
import pygame
print(pygame.get_init())
"""


class TestLoadingPortMidi:
    """Loading PortMidi prints nothing of its own and leaves pygame uninitialized."""

    def test_loading_prints_nothing_and_initializes_nothing(self) -> None:
        result = subprocess.run(
            (sys.executable, "-c", PROBE),
            capture_output=True,
            text=True,
            timeout=IMPORT_SECONDS,
            check=True,
        )

        assert result.stdout.strip() == "False"
