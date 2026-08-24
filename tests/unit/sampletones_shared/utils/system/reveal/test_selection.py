from pathlib import Path
from typing import Callable, Final
from unittest.mock import patch

import pytest

from sampletones_shared.utils.system.modules import JEEPNEY_MODULE, module_available
from sampletones_shared.utils.system.reveal.grouped import GroupedDirectoryBackend
from sampletones_shared.utils.system.reveal.selection import (
    open_paths_in_explorer,
    select_reveal_backend,
)
from sampletones_shared.utils.system.system import System

MODULE = "sampletones_shared.utils.system.reveal.selection"
BACKEND_MODULE = "sampletones_shared.utils.system.reveal.file_manager1"

JEEPNEY_INSTALLED: Final[bool] = module_available(JEEPNEY_MODULE)

requires_jeepney = pytest.mark.skipif(
    not JEEPNEY_INSTALLED,
    reason="The FileManager1 backend stands on jeepney, which ships on Linux",
)


def _available(installed: bool) -> Callable[[str], bool]:
    def resolver(module: str) -> bool:
        return installed

    return resolver


class TestOpenPathsInExplorer:
    def test_a_single_path_opens_the_explorer_on_it(self) -> None:
        path = Path("/a/one.wav")

        with patch(f"{MODULE}.open_path_in_explorer") as open_single:
            open_paths_in_explorer([path])

        open_single.assert_called_once_with(path)

    def test_several_paths_go_through_the_selected_backend(self) -> None:
        paths = (Path("/a/one.wav"), Path("/b/two.wav"))

        with patch(f"{MODULE}.select_reveal_backend") as select:
            open_paths_in_explorer(list(paths))

        select.assert_called_once()
        select.return_value.open.assert_called_once_with(paths)

    def test_no_path_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one path is required"):
            open_paths_in_explorer([])


class TestSelectRevealBackend:
    def test_grouped_on_non_linux_systems(self) -> None:
        with patch(f"{MODULE}.System.current", return_value=System.WINDOWS):
            assert isinstance(select_reveal_backend(), GroupedDirectoryBackend)

    def test_grouped_when_jeepney_is_absent(self) -> None:
        with (
            patch(f"{MODULE}.System.current", return_value=System.LINUX),
            patch(f"{MODULE}.module_available", side_effect=_available(installed=False)),
        ):
            assert isinstance(select_reveal_backend(), GroupedDirectoryBackend)

    @requires_jeepney
    def test_file_manager1_when_the_service_answers(self) -> None:
        from sampletones_shared.utils.system.reveal.file_manager1 import FileManager1Backend

        with (
            patch(f"{MODULE}.System.current", return_value=System.LINUX),
            patch(f"{MODULE}.module_available", side_effect=_available(installed=True)),
            patch(f"{BACKEND_MODULE}.FileManager1Backend.answers", return_value=True),
        ):
            assert isinstance(select_reveal_backend(), FileManager1Backend)

    @requires_jeepney
    def test_grouped_when_the_service_stays_silent(self) -> None:
        with (
            patch(f"{MODULE}.System.current", return_value=System.LINUX),
            patch(f"{MODULE}.module_available", side_effect=_available(installed=True)),
            patch(f"{BACKEND_MODULE}.FileManager1Backend.answers", return_value=False),
        ):
            assert isinstance(select_reveal_backend(), GroupedDirectoryBackend)
