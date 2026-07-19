import os
from typing import Callable, Optional
from unittest.mock import patch

from sampletones_application.utils.file_dialogs.kdialog import KDialogBackend
from sampletones_application.utils.file_dialogs.selection import select_file_dialog_backend
from sampletones_application.utils.file_dialogs.tkinter_backend import TkinterBackend
from sampletones_application.utils.file_dialogs.zenity import ZenityBackend
from sampletones_shared.utils.system.system import System

MODULE = "sampletones_application.utils.file_dialogs.selection"


def _which(*, kdialog: bool, zenity: bool) -> Callable[[str], Optional[str]]:
    available = {"kdialog": kdialog, "zenity": zenity}

    def resolver(tool: str) -> Optional[str]:
        return f"/usr/bin/{tool}" if available.get(tool, False) else None

    return resolver


class TestSelectFileDialogBackend:
    def test_windows_uses_tkinter(self) -> None:
        with patch(f"{MODULE}.System.current", return_value=System.WINDOWS):
            assert isinstance(select_file_dialog_backend(), TkinterBackend)

    def test_macos_uses_tkinter(self) -> None:
        with patch(f"{MODULE}.System.current", return_value=System.MACOS):
            assert isinstance(select_file_dialog_backend(), TkinterBackend)

    def test_kde_prefers_kdialog(self) -> None:
        with (
            patch(f"{MODULE}.System.current", return_value=System.LINUX),
            patch(f"{MODULE}.shutil.which", side_effect=_which(kdialog=True, zenity=True)),
            patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}, clear=False),
        ):
            assert isinstance(select_file_dialog_backend(), KDialogBackend)

    def test_gnome_prefers_zenity(self) -> None:
        with (
            patch(f"{MODULE}.System.current", return_value=System.LINUX),
            patch(f"{MODULE}.shutil.which", side_effect=_which(kdialog=True, zenity=True)),
            patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}, clear=False),
        ):
            assert isinstance(select_file_dialog_backend(), ZenityBackend)

    def test_kde_without_kdialog_falls_back_to_zenity(self) -> None:
        with (
            patch(f"{MODULE}.System.current", return_value=System.LINUX),
            patch(f"{MODULE}.shutil.which", side_effect=_which(kdialog=False, zenity=True)),
            patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}, clear=False),
        ):
            assert isinstance(select_file_dialog_backend(), ZenityBackend)

    def test_no_linux_tools_uses_tkinter(self) -> None:
        with (
            patch(f"{MODULE}.System.current", return_value=System.LINUX),
            patch(f"{MODULE}.shutil.which", side_effect=_which(kdialog=False, zenity=False)),
            patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}, clear=False),
        ):
            assert isinstance(select_file_dialog_backend(), TkinterBackend)
