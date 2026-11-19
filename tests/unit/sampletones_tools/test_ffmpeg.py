from typing import Final
from unittest.mock import patch

import pytest

from sampletones_shared.utils.system.system import System
from sampletones_tools.ffmpeg import FFMPEG, INSTALL_HINTS, missing_ffmpeg_message

PURPOSE: Final[str] = "frames are encoded into a video"


class TestMissingFfmpegMessage:
    """What a tool reports when ffmpeg is absent."""

    @pytest.mark.parametrize("system", list(System))
    def test_every_system_names_ffmpeg_the_purpose_and_its_own_install_command(self, system: System) -> None:
        with patch.object(System, "current", return_value=system):
            message = missing_ffmpeg_message(PURPOSE)

        assert FFMPEG in message
        assert PURPOSE in message
        assert INSTALL_HINTS[system] in message
