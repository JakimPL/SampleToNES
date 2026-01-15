from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import List
from unittest.mock import MagicMock, call, patch

import pytest

from sampletones.typehints.general import GeneralPathlike
from sampletones.utils.paths import (
    get_directory,
    open_directory_in_explorer_linux,
    open_file_in_explorer_linux,
    open_path_in_explorer,
    shorten_path,
    to_path,
)
from sampletones.utils.system import System


class TestToPath:
    def test_to_path_with_unix_absolute_string(self) -> None:
        result = to_path("/home/user/file.txt")
        assert isinstance(result, Path)
        assert str(result) == "/home/user/file.txt"

    def test_to_path_with_windows_absolute_string(self) -> None:
        result = to_path("C:\\Users\\user\\file.txt")
        assert isinstance(result, Path)
        assert str(result) == "C:\\Users\\user\\file.txt"

    def test_to_path_with_windows_forward_slash_string(self) -> None:
        result = to_path("C:/Users/user/file.txt")
        assert isinstance(result, Path)
        assert "Users" in str(result) and "user" in str(result)

    def test_to_path_with_windows_unc_path(self) -> None:
        result = to_path("\\\\server\\share\\file.txt")
        assert isinstance(result, Path)
        assert "server" in str(result)

    def test_to_path_with_path_object(self) -> None:
        path = Path("/home/user/file.txt")
        result = to_path(path)
        assert isinstance(result, Path)
        assert result == path

    def test_to_path_with_relative_string(self) -> None:
        result = to_path("relative/path/file.txt")
        assert isinstance(result, Path)
        assert str(result) == "relative/path/file.txt"

    def test_to_path_with_current_directory_dot(self) -> None:
        result = to_path(".")
        assert isinstance(result, Path)
        assert str(result) == "."

    def test_to_path_with_parent_directory_dots(self) -> None:
        result = to_path("..")
        assert isinstance(result, Path)
        assert str(result) == ".."

    def test_to_path_with_triple_dots_in_name(self) -> None:
        result = to_path("/home/.../file.txt")
        assert isinstance(result, Path)
        assert "..." in str(result)

    def test_to_path_with_mixed_separators(self) -> None:
        result = to_path("folder/subfolder\\file.txt")
        assert isinstance(result, Path)

    def test_to_path_with_trailing_slash(self) -> None:
        result = to_path("/home/user/")
        assert isinstance(result, Path)

    def test_to_path_with_multiple_consecutive_slashes(self) -> None:
        result = to_path("/home//user///file.txt")
        assert isinstance(result, Path)

    def test_to_path_with_spaces_in_path(self) -> None:
        result = to_path("/home/user/my file.txt")
        assert isinstance(result, Path)
        assert "my file.txt" in str(result)

    def test_to_path_with_special_characters(self) -> None:
        result = to_path("/home/user/file@#$.txt")
        assert isinstance(result, Path)

    def test_to_path_with_integer_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be str or Path, got <class 'int'>"):
            to_path(42)  # type: ignore

    def test_to_path_with_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be str or Path, got <class 'list'>"):
            to_path(["/home/user"])  # type: ignore

    def test_to_path_with_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be str or Path, got <class 'NoneType'>"):
            to_path(None)  # type: ignore

    def test_to_path_with_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be str or Path, got <class 'dict'>"):
            to_path({"path": "/home"})  # type: ignore

    def test_to_path_with_empty_string(self) -> None:
        result = to_path("")
        assert isinstance(result, Path)
        assert str(result) == "."

    def test_to_path_preserves_path_instance(self) -> None:
        original = Path("/home/user/file.txt")
        result = to_path(original)
        assert result is original


class TestShortenPath:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False
        input_path: GeneralPathlike
        resolved_path: GeneralPathlike
        levels: int
        expected_result: str
        test_id: str
        os_sep: str = "/"

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                input_path=PurePosixPath("/home/user/file.txt"),
                resolved_path=PurePosixPath("/home/user/file.txt"),
                levels=5,
                expected_result="/home/user/file.txt",
                test_id="short_unix_path",
            ),
            TestCase(
                input_path=PurePosixPath("/home/user/some/long/path/to/the/file.txt"),
                resolved_path=PurePosixPath("/home/user/some/long/path/to/the/file.txt"),
                levels=5,
                expected_result="/home/.../to/the/file.txt",
                test_id="long_unix_path",
            ),
            TestCase(
                input_path=PurePosixPath("/a/b/c/d/e"),
                resolved_path=PurePosixPath("/a/b/c/d/e"),
                levels=5,
                expected_result="/a/b/c/d/e",
                test_id="exact_levels_unix",
            ),
            TestCase(
                input_path=PurePosixPath("/a/b/c/d/e/f/g/h"),
                resolved_path=PurePosixPath("/a/b/c/d/e/f/g/h"),
                levels=4,
                expected_result="/a/.../g/h",
                test_id="custom_levels_4",
            ),
            TestCase(
                input_path=PurePosixPath("/a/b/c/d/e"),
                resolved_path=PurePosixPath("/a/b/c/d/e"),
                levels=3,
                expected_result="/a/.../e",
                test_id="custom_levels_3",
            ),
            TestCase(
                input_path=PurePosixPath("/a/b/c/d/e/f/g"),
                resolved_path=PurePosixPath("/a/b/c/d/e/f/g"),
                levels=2,
                expected_result="/.../g",
                test_id="custom_levels_2",
            ),
            TestCase(
                input_path=PurePosixPath("/home/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/dir9/dir10/file.txt"),
                resolved_path=PurePosixPath("/home/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/dir9/dir10/file.txt"),
                levels=5,
                expected_result="/home/.../dir9/dir10/file.txt",
                test_id="very_long_unix_path",
            ),
            TestCase(
                input_path=PureWindowsPath("C:/Users/user/file.txt"),
                resolved_path=PureWindowsPath("C:/Users/user/file.txt"),
                levels=5,
                expected_result="C:\\Users\\user\\file.txt",
                test_id="windows_path_short",
                os_sep="\\",
            ),
            TestCase(
                input_path=PureWindowsPath("C:/Users/user/Documents/Projects/Python/MyApp/src/main.py"),
                resolved_path=PureWindowsPath("C:/Users/user/Documents/Projects/Python/MyApp/src/main.py"),
                levels=4,
                expected_result="C:\\Users\\...\\src\\main.py",
                os_sep="\\",
                test_id="windows_path_long",
            ),
            TestCase(
                input_path=PurePosixPath("/home/folder1/folder2/folder3/folder4/.../file.txt"),
                resolved_path=PurePosixPath("/home/folder1/folder2/folder3/folder4/file.txt"),
                levels=3,
                expected_result="/home/.../file.txt",
                test_id="containing_literal_dots",
            ),
            TestCase(
                input_path=PurePosixPath("relative/path/to/file.txt"),
                resolved_path=PurePosixPath("/absolute/resolved/relative/path/to/file.txt"),
                levels=5,
                expected_result="/absolute/.../path/to/file.txt",
                test_id="relative_path_resolved",
            ),
            TestCase(
                input_path=PurePosixPath("/home/user/folder/../other/file.txt"),
                resolved_path=PurePosixPath("/home/user/other/file.txt"),
                levels=5,
                expected_result="/home/user/other/file.txt",
                test_id="parent_directory_references",
            ),
            TestCase(
                input_path=PurePosixPath("/home/./user/./file.txt"),
                resolved_path=PurePosixPath("/home/user/file.txt"),
                levels=5,
                expected_result="/home/user/file.txt",
                test_id="current_directory_references",
            ),
            TestCase(
                input_path=PurePosixPath("/"),
                resolved_path=PurePosixPath("/"),
                levels=5,
                expected_result="/",
                test_id="root_only",
            ),
            TestCase(
                input_path=PurePosixPath("/home"),
                resolved_path=PurePosixPath("/home"),
                levels=5,
                expected_result="/home",
                test_id="two_parts_unix",
            ),
            TestCase(
                input_path=PureWindowsPath("C:/"),
                resolved_path=PureWindowsPath("C:/"),
                levels=5,
                os_sep="\\",
                expected_result="C:\\",
                test_id="windows_drive_only",
            ),
            TestCase(
                input_path=PurePosixPath("relative/./path/to/../file.txt"),
                resolved_path=PurePosixPath("/absolute/relative/path/file.txt"),
                levels=4,
                expected_result="/absolute/relative/path/file.txt",
                test_id="relative_with_dots_resolved",
            ),
            TestCase(
                input_path=PureWindowsPath("C:/Program Files/App/nested/very/deep/folder/file.exe"),
                resolved_path=PureWindowsPath("C:/Program Files/App/nested/very/deep/folder/file.exe"),
                levels=6,
                os_sep="\\",
                expected_result="C:\\Program Files\\...\\very\\deep\\folder\\file.exe",
                test_id="windows_with_spaces",
            ),
        ],
        ids=lambda tc: tc.test_id,
    )
    def test_shorten_path(
        self,
        test_case: TestShortenPath.TestCase,
    ) -> None:
        with patch("sampletones.utils.paths.Path.expanduser") as mock_expand:
            with patch("sampletones.utils.paths.Path.resolve") as mock_resolve:
                with patch("sampletones.utils.paths.os.sep", test_case.os_sep):
                    resolved_mock = MagicMock()
                    resolved_mock.parts = test_case.resolved_path.parts
                    resolved_mock.__str__ = MagicMock(return_value=str(test_case.resolved_path))

                    mock_expand.return_value.resolve.return_value = resolved_mock
                    mock_resolve.return_value = resolved_mock

                    result = shorten_path(test_case.input_path, levels=test_case.levels)
                    assert result == test_case.expected_result

    def test_shorten_path_with_integer_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be path-like, got <class 'int'>"):
            shorten_path(42, levels=5)  # type: ignore

    def test_shorten_path_with_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be path-like, got <class 'NoneType'>"):
            shorten_path(None, levels=5)  # type: ignore

    def test_shorten_path_with_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be path-like, got <class 'dict'>"):
            shorten_path({"path": "/home"}, levels=5)  # type: ignore

    def test_shorten_path_with_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be path-like, got <class 'list'>"):
            shorten_path(["/home", "user"], levels=5)  # type: ignore

    def test_shorten_path_with_negative_levels_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Levels must be a positive integer greater than 1"):
            shorten_path(Path("/home/user/file.txt"), levels=-5)

    def test_shorten_path_with_zero_levels_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Levels must be a positive integer greater than 1"):
            shorten_path(Path("/home/user/file.txt"), levels=0)

    def test_shorten_path_with_one_level_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Levels must be a positive integer greater than 1"):
            shorten_path(Path("/home/user/file.txt"), levels=1)

    def test_shorten_path_with_float_levels_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Levels must be a positive integer greater than 1"):
            shorten_path(Path("/home/user/file.txt"), levels=5.5)  # type: ignore

    def test_shorten_path_with_string_levels_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Levels must be a positive integer greater than 1"):
            shorten_path(Path("/home/user/file.txt"), levels="5")  # type: ignore


class TestGetDirectory:
    def test_get_directory_with_directory_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_directory(tmpdir)
            assert result == Path(tmpdir)
            assert result.is_dir()

    def test_get_directory_with_directory_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            result = get_directory(path)
            assert result == path
            assert result.is_dir()

    def test_get_directory_with_file_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            filepath.touch()
            result = get_directory(str(filepath))
            assert result == Path(tmpdir)
            assert result.is_dir()

    def test_get_directory_with_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            filepath.touch()
            result = get_directory(filepath)
            assert result == Path(tmpdir)
            assert result.is_dir()

    def test_get_directory_with_integer_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be str or Path, got <class 'int'>"):
            get_directory(123)  # type: ignore

    def test_get_directory_with_nonexistent_path(self) -> None:
        path = Path("/nonexistent/path/file.txt")
        result = get_directory(path)
        assert result == Path("/nonexistent/path")

    def test_get_directory_nested_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "sub1" / "sub2"
            subdir.mkdir(parents=True)
            filepath = subdir / "file.txt"
            filepath.touch()

            result = get_directory(filepath)
            assert result == subdir
            assert result.is_dir()

    def test_get_directory_with_current_directory(self) -> None:
        result = get_directory(".")
        assert isinstance(result, Path)

    def test_get_directory_with_parent_directory(self) -> None:
        result = get_directory("..")
        assert isinstance(result, Path)

    def test_get_directory_with_triple_dots(self) -> None:
        path = Path("/home/.../file.txt")
        result = get_directory(path)
        assert result == Path("/home/...")

    def test_get_directory_with_relative_path_containing_dots(self) -> None:
        path = Path("folder/../other/file.txt")
        result = get_directory(path)
        assert isinstance(result, Path)


class TestOpenDirectoryInExplorerLinux:
    @patch("sampletones.utils.paths.subprocess.run")
    def test_open_with_directory(self, mock_run: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            open_directory_in_explorer_linux(path)

            mock_run.assert_called_once_with(["xdg-open", tmpdir], check=False)

    @patch("sampletones.utils.paths.subprocess.run")
    def test_open_with_file(self, mock_run: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            filepath.touch()

            open_directory_in_explorer_linux(filepath)

            mock_run.assert_called_once_with(["xdg-open", tmpdir], check=False)


class TestOpenFileInExplorerLinux:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        desktop_file: str
        expected_command: List[str]
        path: str
        mime_returncode: int
        command_returncode: int
        should_fallback: bool

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                test_id="dolphin_kde",
                desktop_file="org.kde.dolphin.desktop",
                expected_command=["dolphin", "--select", "/tmp/test.txt"],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=False,
            ),
            TestCase(
                test_id="dolphin_plain",
                desktop_file="dolphin.desktop",
                expected_command=["dolphin", "--select", "/tmp/test.txt"],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=False,
            ),
            TestCase(
                test_id="nautilus_gnome",
                desktop_file="org.gnome.Nautilus.desktop",
                expected_command=["nautilus", "--select", "/tmp/test.txt"],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=False,
            ),
            TestCase(
                test_id="nautilus_plain",
                desktop_file="nautilus.desktop",
                expected_command=["nautilus", "--select", "/tmp/test.txt"],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=False,
            ),
            TestCase(
                test_id="nemo",
                desktop_file="nemo.desktop",
                expected_command=["nemo", "/tmp/test.txt"],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=False,
            ),
            TestCase(
                test_id="thunar",
                desktop_file="thunar.desktop",
                expected_command=["thunar", "/tmp/test.txt"],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=False,
            ),
            TestCase(
                test_id="whitespace_in_path",
                desktop_file="org.kde.dolphin.desktop",
                expected_command=["dolphin", "--select", "/tmp/file with spaces.txt"],
                path="/tmp/file with spaces.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=False,
            ),
            TestCase(
                test_id="unknown_file_manager",
                desktop_file="unknown.desktop",
                expected_command=[],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=0,
                should_fallback=True,
            ),
            TestCase(
                test_id="mime_query_fails",
                desktop_file="",
                expected_command=[],
                path="/tmp/test.txt",
                mime_returncode=1,
                command_returncode=0,
                should_fallback=True,
            ),
            TestCase(
                test_id="command_execution_fails",
                desktop_file="org.kde.dolphin.desktop",
                expected_command=["dolphin", "--select", "/tmp/test.txt"],
                path="/tmp/test.txt",
                mime_returncode=0,
                command_returncode=1,
                should_fallback=True,
            ),
        ],
        ids=lambda tc: tc.test_id,
    )
    @patch("sampletones.utils.paths.subprocess.run")
    @patch("sampletones.utils.paths.open_directory_in_explorer_linux")
    def test_open_file_in_explorer_linux(
        self,
        mock_open_dir: MagicMock,
        mock_run: MagicMock,
        test_case: TestOpenFileInExplorerLinux.TestCase,
    ) -> None:
        if test_case.should_fallback:
            if test_case.mime_returncode == 1:
                mock_run.return_value = MagicMock(returncode=test_case.mime_returncode)
            elif test_case.desktop_file == "unknown.desktop":
                mock_run.return_value = MagicMock(returncode=0, stdout=f"{test_case.desktop_file}\n")
            else:
                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout=f"{test_case.desktop_file}\n"),
                    MagicMock(returncode=test_case.command_returncode),
                ]

            path = Path(test_case.path)
            open_file_in_explorer_linux(path)
            mock_open_dir.assert_called_once_with(path)
        else:
            mock_run.side_effect = [
                MagicMock(returncode=test_case.mime_returncode, stdout=f"{test_case.desktop_file}\n"),
                MagicMock(returncode=test_case.command_returncode),
            ]

            path = Path(test_case.path)
            open_file_in_explorer_linux(path)

            assert mock_run.call_count == 2
            assert mock_run.call_args_list[1] == call(test_case.expected_command, check=False, capture_output=True)


class TestOpenPathInExplorer:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        system: System
        is_file: bool
        expected_command: List[str]

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                test_id="windows_file",
                system=System.WINDOWS,
                is_file=True,
                expected_command=["explorer", "/select,"],
            ),
            TestCase(
                test_id="windows_directory",
                system=System.WINDOWS,
                is_file=False,
                expected_command=["explorer", ""],
            ),
            TestCase(
                test_id="macos_file",
                system=System.MACOS,
                is_file=True,
                expected_command=["open", "-R"],
            ),
            TestCase(
                test_id="macos_directory",
                system=System.MACOS,
                is_file=False,
                expected_command=["open", ""],
            ),
        ],
        ids=lambda tc: tc.test_id,
    )
    @patch("sampletones.utils.paths.System.current")
    @patch("sampletones.utils.paths.subprocess.run")
    def test_cross_platform(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        test_case: TestOpenPathInExplorer.TestCase,
    ) -> None:
        mock_system.return_value = test_case.system

        with tempfile.TemporaryDirectory() as tmpdir:
            if test_case.is_file:
                path = Path(tmpdir) / "test.txt"
                path.touch()
            else:
                path = Path(tmpdir)

            open_path_in_explorer(path)

            expected = test_case.expected_command + [str(path)]
            mock_run.assert_called_once_with(expected, check=False)

    @pytest.mark.parametrize(
        "is_file",
        [True, False],
        ids=["linux_file", "linux_directory"],
    )
    @patch("sampletones.utils.paths.System.current")
    @patch("sampletones.utils.paths.open_file_in_explorer_linux")
    @patch("sampletones.utils.paths.subprocess.run")
    def test_linux(
        self,
        mock_run: MagicMock,
        mock_open_file: MagicMock,
        mock_system: MagicMock,
        is_file: bool,
    ) -> None:
        mock_system.return_value = System.LINUX

        with tempfile.TemporaryDirectory() as tmpdir:
            if is_file:
                filepath = Path(tmpdir) / "test.txt"
                filepath.touch()
                open_path_in_explorer(filepath)
                mock_open_file.assert_called_once_with(filepath)
                mock_run.assert_not_called()
            else:
                path = Path(tmpdir)
                open_path_in_explorer(path)
                mock_open_file.assert_not_called()
                mock_run.assert_called_once_with(["xdg-open", tmpdir], check=False)

    @patch("sampletones.utils.paths.System.current")
    def test_unsupported_os(self, mock_system: MagicMock) -> None:
        mock_system.return_value = "UnsupportedOS"

        path = Path("/tmp/test.txt")

        with pytest.raises(OSError, match="Unsupported operating system: UnsupportedOS"):
            open_path_in_explorer(path)

    @patch("sampletones.utils.paths.System.current")
    @patch("sampletones.utils.paths.subprocess.run")
    def test_with_string_path(self, mock_run: MagicMock, mock_system: MagicMock) -> None:
        mock_system.return_value = System.LINUX

        with tempfile.TemporaryDirectory() as tmpdir:
            path_str = str(tmpdir)
            open_path_in_explorer(path_str)
            mock_run.assert_called_once_with(["xdg-open", tmpdir], check=False)

    def test_with_integer_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be str or Path, got <class 'int'>"):
            open_path_in_explorer(42)  # type: ignore
