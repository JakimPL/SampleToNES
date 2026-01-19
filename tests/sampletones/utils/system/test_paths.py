from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, List, Type, Union
from unittest.mock import MagicMock, call, patch

import pytest

from sampletones.typehints.general import GeneralPathlike
from sampletones.utils.system.paths import (
    get_directory,
    open_directory_in_explorer_linux,
    open_file_in_explorer_linux,
    open_path_in_explorer,
    shorten_path,
    to_path,
)
from sampletones.utils.system.system import System
from tests.sampletones.errors import expect_error


class TestToPath:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        input_path: Any
        expected_result: Union[str, Type[Exception]]
        test_id: str

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                input_path="/home/user/file.txt",
                expected_result="/home/user/file.txt",
                test_id="unix_absolute_string",
            ),
            TestCase(
                input_path="C:\\Users\\user\\file.txt",
                expected_result="C:\\Users\\user\\file.txt",
                test_id="windows_absolute_string",
            ),
            TestCase(
                input_path="C:/Users/user/file.txt",
                expected_result="C:/Users/user/file.txt",
                test_id="windows_forward_slash_string",
            ),
            TestCase(
                input_path="\\\\server\\share\\file.txt",
                expected_result="\\\\server\\share\\file.txt",
                test_id="windows_unc_path",
            ),
            TestCase(
                input_path=Path("/home/user/file.txt"),
                expected_result="/home/user/file.txt",
                test_id="path_object",
            ),
            TestCase(
                input_path="relative/path/file.txt",
                expected_result="relative/path/file.txt",
                test_id="relative_string",
            ),
            TestCase(
                input_path=".",
                expected_result=".",
                test_id="current_directory_dot",
            ),
            TestCase(
                input_path="..",
                expected_result="..",
                test_id="parent_directory_dots",
            ),
            TestCase(
                input_path="/home/.../file.txt",
                expected_result="/home/.../file.txt",
                test_id="triple_dots_in_name",
            ),
            TestCase(
                input_path="folder/subfolder\\file.txt",
                expected_result="folder/subfolder\\file.txt",
                test_id="mixed_separators",
            ),
            TestCase(
                input_path="/home/user/",
                expected_result="/home/user",
                test_id="trailing_slash",
            ),
            TestCase(
                input_path="/home//user///file.txt",
                expected_result="/home/user/file.txt",
                test_id="multiple_consecutive_slashes",
            ),
            TestCase(
                input_path="/home/user/my file.txt",
                expected_result="/home/user/my file.txt",
                test_id="spaces_in_path",
            ),
            TestCase(
                input_path="/home/user/file@#$.txt",
                expected_result="/home/user/file@#$.txt",
                test_id="special_characters",
            ),
            TestCase(
                input_path="",
                expected_result=".",
                test_id="empty_string",
            ),
            TestCase(
                input_path=Path("/home/user/file.txt"),
                expected_result="/home/user/file.txt",
                test_id="preserves_path_instance",
            ),
            TestCase(
                input_path=42,
                expected_result=TypeError,
                test_id="integer_raises_type_error",
            ),
            TestCase(
                input_path=["/home/user"],
                expected_result=TypeError,
                test_id="list_raises_type_error",
            ),
            TestCase(
                input_path=None,
                expected_result=TypeError,
                test_id="none_raises_type_error",
            ),
            TestCase(
                input_path={"path": "/home"},
                expected_result=TypeError,
                test_id="dict_raises_type_error",
            ),
        ],
        ids=lambda tc: tc.test_id,
    )
    def test_to_path(self, test_case: TestToPath.TestCase) -> None:
        if expect_error(to_path, test_case.expected_result, test_case.input_path):
            return

        result = to_path(test_case.input_path)
        assert isinstance(result, Path)

        if isinstance(test_case.input_path, Path):
            assert result is test_case.input_path

        assert str(result) == test_case.expected_result


class TestShortenPath:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False
        input_path: Any
        resolved_path: Any
        levels: Any
        expected_result: Union[str, Type[Exception]]
        test_id: str
        os_sep: str = "/"

    def _create_resolved_mock(self, resolved_path: GeneralPathlike) -> MagicMock:
        resolved_mock = MagicMock()
        try:
            resolved_mock.parts = Path(resolved_path).parts
            resolved_mock.__str__ = MagicMock(return_value=str(resolved_path))  # type: ignore[method-assign]
        except TypeError:
            resolved_mock.parts = ()

        return resolved_mock

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
            TestCase(
                input_path=42,
                resolved_path=None,
                levels=5,
                expected_result=TypeError,
                test_id="integer_path_raises_type_error",
            ),
            TestCase(
                input_path=None,
                resolved_path=None,
                levels=5,
                expected_result=TypeError,
                test_id="none_path_raises_type_error",
            ),
            TestCase(
                input_path={"path": "/home"},
                resolved_path=None,
                levels=5,
                expected_result=TypeError,
                test_id="dict_path_raises_type_error",
            ),
            TestCase(
                input_path=["/home", "user"],
                resolved_path=None,
                levels=5,
                expected_result=TypeError,
                test_id="list_path_raises_type_error",
            ),
            TestCase(
                input_path=PurePosixPath("/home/user/file.txt"),
                resolved_path=PurePosixPath("/home/user/file.txt"),
                levels=-5,
                expected_result=ValueError,
                test_id="negative_levels_raises_value_error",
            ),
            TestCase(
                input_path=PurePosixPath("/home/user/file.txt"),
                resolved_path=PurePosixPath("/home/user/file.txt"),
                levels=0,
                expected_result=ValueError,
                test_id="zero_levels_raises_value_error",
            ),
            TestCase(
                input_path=PurePosixPath("/home/user/file.txt"),
                resolved_path=PurePosixPath("/home/user/file.txt"),
                levels=1,
                expected_result=ValueError,
                test_id="one_level_raises_value_error",
            ),
            TestCase(
                input_path=PurePosixPath("/home/user/file.txt"),
                resolved_path=PurePosixPath("/home/user/file.txt"),
                levels=5.5,
                expected_result=ValueError,
                test_id="float_levels_raises_value_error",
            ),
            TestCase(
                input_path=PurePosixPath("/home/user/file.txt"),
                resolved_path=PurePosixPath("/home/user/file.txt"),
                levels="5",
                expected_result=ValueError,
                test_id="string_levels_raises_value_error",
            ),
        ],
        ids=lambda tc: tc.test_id,
    )
    def test_shorten_path(
        self,
        test_case: TestShortenPath.TestCase,
    ) -> None:
        with (
            patch("sampletones.utils.system.paths.Path.expanduser") as mock_expand,
            patch("sampletones.utils.system.paths.Path.resolve") as mock_resolve,
            patch("sampletones.utils.system.paths.os.sep", test_case.os_sep),
        ):
            resolved_mock = self._create_resolved_mock(test_case.resolved_path)
            mock_expand.return_value.resolve.return_value = resolved_mock
            mock_resolve.return_value = resolved_mock

            if expect_error(
                shorten_path,
                test_case.expected_result,
                test_case.input_path,
                test_case.levels,
            ):
                return

            result = shorten_path(test_case.input_path, levels=test_case.levels)
            assert result == test_case.expected_result


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
            get_directory(123)

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
    @patch("sampletones.utils.system.paths.subprocess.run")
    def test_open_with_directory(self, mock_run: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            open_directory_in_explorer_linux(path)

            mock_run.assert_called_once_with(["xdg-open", tmpdir], check=False)

    @patch("sampletones.utils.system.paths.subprocess.run")
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
    @patch("sampletones.utils.system.paths.subprocess.run")
    @patch("sampletones.utils.system.paths.open_directory_in_explorer_linux")
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
    @patch("sampletones.utils.system.paths.System.current")
    @patch("sampletones.utils.system.paths.subprocess.run")
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
    @patch("sampletones.utils.system.paths.System.current")
    @patch("sampletones.utils.system.paths.open_file_in_explorer_linux")
    @patch("sampletones.utils.system.paths.subprocess.run")
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

    @patch("sampletones.utils.system.paths.System.current")
    def test_unsupported_os(self, mock_system: MagicMock) -> None:
        mock_system.return_value = "UnsupportedOS"

        path = Path("/tmp/test.txt")

        with pytest.raises(OSError, match="Unsupported operating system: UnsupportedOS"):
            open_path_in_explorer(path)

    @patch("sampletones.utils.system.paths.System.current")
    @patch("sampletones.utils.system.paths.subprocess.run")
    def test_with_string_path(self, mock_run: MagicMock, mock_system: MagicMock) -> None:
        mock_system.return_value = System.LINUX

        with tempfile.TemporaryDirectory() as tmpdir:
            path_str = str(tmpdir)
            open_path_in_explorer(path_str)
            mock_run.assert_called_once_with(["xdg-open", tmpdir], check=False)

    def test_with_integer_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected path to be str or Path, got <class 'int'>"):
            open_path_in_explorer(42)
