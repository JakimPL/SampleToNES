from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from unittest.mock import patch

import pytest

from sampletones_application.utils.file import open_file_dialog, save_file_dialog
from sampletones_shared.utils.system.system import System
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestSaveFileDialog(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        returned: str
        extensions: Tuple[str, ...]
        expected: Optional[str]

    test_cases = [
        TestCase(
            returned="song",
            extensions=(".stp",),
            expected="song.stp",
            label="appends_missing_extension",
        ),
        TestCase(
            returned="song.stp",
            extensions=(".stp",),
            expected="song.stp",
            label="keeps_present_extension",
        ),
        TestCase(
            returned="song.STP",
            extensions=(".stp",),
            expected="song.STP",
            label="keeps_present_extension_case_insensitively",
        ),
        TestCase(
            returned="song.txt",
            extensions=(".stp",),
            expected="song.txt.stp",
            label="appends_after_foreign_extension",
        ),
        TestCase(
            returned="",
            extensions=(".stp",),
            expected=None,
            label="cancel_returns_none",
        ),
        TestCase(
            returned="song",
            extensions=(),
            expected="song",
            label="no_extension_configured_keeps_name",
        ),
        TestCase(
            returned="/home/user/song",
            extensions=(".stp",),
            expected="/home/user/song.stp",
            label="appends_on_full_path",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_save_file_dialog_extension(self, test_case: TestCase) -> None:
        with patch("sampletones_application.utils.file.filedialpy.saveFile") as mock_save:
            mock_save.return_value = test_case.returned
            result = save_file_dialog(title="Save", extensions=test_case.extensions)

        if test_case.expected is None:
            assert result is None
        else:
            assert result == Path(test_case.expected)

    def test_forwards_normalized_extension_filter(self) -> None:
        with patch("sampletones_application.utils.file.filedialpy.saveFile") as mock_save:
            mock_save.return_value = "song.stp"
            save_file_dialog(title="Save", extensions=[".stp"])

        assert mock_save.call_args.kwargs["filter"] == ["*.stp"]


class TestOpenFileDialog:
    def test_cancel_returns_none(self) -> None:
        with patch("sampletones_application.utils.file.filedialpy.openFile") as mock_open:
            mock_open.return_value = ""
            result = open_file_dialog(title="Open", extensions=[".wav"])

        assert result is None

    def test_returns_selected_path(self) -> None:
        with patch("sampletones_application.utils.file.filedialpy.openFile") as mock_open:
            mock_open.return_value = "/home/user/audio.wav"
            result = open_file_dialog(title="Open", extensions=[".wav"])

        assert result == Path("/home/user/audio.wav")


class TestMacOSHardening:
    """Guards the macOS-specific filedialpy workarounds without a macOS host."""

    def test_open_forwards_space_joined_filter_on_macos(self) -> None:
        with (
            patch("sampletones_application.utils.file.System.current", return_value=System.MACOS),
            patch("sampletones_application.utils.file.filedialpy.openFile") as mock_open,
        ):
            mock_open.return_value = "/home/user/audio.wav"
            open_file_dialog(title="Open", extensions=[".wav", ".mp3"])

        assert mock_open.call_args.kwargs["filter"] == "*.wav *.mp3"

    def test_open_forwards_none_filter_without_extensions_on_macos(self) -> None:
        with (
            patch("sampletones_application.utils.file.System.current", return_value=System.MACOS),
            patch("sampletones_application.utils.file.filedialpy.openFile") as mock_open,
        ):
            mock_open.return_value = "/home/user/audio.wav"
            open_file_dialog(title="Open")

        assert mock_open.call_args.kwargs["filter"] is None

    def test_open_forwards_list_filter_off_macos(self) -> None:
        with (
            patch("sampletones_application.utils.file.System.current", return_value=System.LINUX),
            patch("sampletones_application.utils.file.filedialpy.openFile") as mock_open,
        ):
            mock_open.return_value = "/home/user/audio.wav"
            open_file_dialog(title="Open", extensions=[".wav", ".mp3"])

        assert mock_open.call_args.kwargs["filter"] == ["*.wav", "*.mp3"]

    def test_open_cancel_returning_cwd_is_discarded_on_macos(self) -> None:
        with (
            patch("sampletones_application.utils.file.System.current", return_value=System.MACOS),
            patch("sampletones_application.utils.file.filedialpy.openFile") as mock_open,
        ):
            mock_open.return_value = str(Path.cwd())
            result = open_file_dialog(title="Open", extensions=[".wav"])

        assert result is None

    def test_save_cancel_returning_cwd_is_discarded_on_macos(self) -> None:
        with (
            patch("sampletones_application.utils.file.System.current", return_value=System.MACOS),
            patch("sampletones_application.utils.file.filedialpy.saveFile") as mock_save,
        ):
            mock_save.return_value = str(Path.cwd())
            result = save_file_dialog(title="Save", extensions=[".stp"])

        assert result is None

    def test_cwd_result_is_kept_off_macos(self) -> None:
        with (
            patch("sampletones_application.utils.file.System.current", return_value=System.LINUX),
            patch("sampletones_application.utils.file.filedialpy.openFile") as mock_open,
        ):
            mock_open.return_value = str(Path.cwd())
            result = open_file_dialog(title="Open", extensions=[".wav"])

        assert result == Path.cwd()
