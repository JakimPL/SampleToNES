from unittest.mock import patch

import pytest

from sampletones.utils.system.system import System


def test_current_system() -> None:
    with patch("platform.system") as mock_system:
        mock_system.return_value = "Windows"
        assert System.current() == System.WINDOWS

        mock_system.return_value = "Linux"
        assert System.current() == System.LINUX

        mock_system.return_value = "Darwin"
        assert System.current() == System.MACOS

        mock_system.return_value = "UnsupportedOS"
        with pytest.raises(OSError, match="Unsupported operating system: UnsupportedOS"):
            System.current()
