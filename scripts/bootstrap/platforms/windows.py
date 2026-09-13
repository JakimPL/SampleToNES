from pathlib import Path
from typing import Final, Optional, Sequence, Tuple

WINDOWS: Final[str] = "Windows"
WINDOWS_LAUNCHER: Final[str] = "sampletones.exe"
BUNDLE_DIRECTORY: Final[str] = "sampletones"
WINDOWS_INTERPRETER: Final[Tuple[str, str]] = ("Scripts", "python.exe")
ICO_ICON: Final[str] = "src/sampletones_assets/icons/sampletones.ico"


class Windows:
    """Windows: the official Python installer carries what the application needs."""

    @property
    def name(self) -> str:
        return WINDOWS

    @property
    def bundles(self) -> bool:
        return True

    @property
    def icon(self) -> str:
        return ICO_ICON

    @property
    def pyaudio_advice(self) -> str:
        return "Run install.bat from the project root to reinstall the dependencies."

    @property
    def tkinter_advice(self) -> str:
        return "Install Python from python.org or the Microsoft Store, which both include Tk, then build again."

    @property
    def tkinter_warning(self) -> str:
        return "This bundle opens no file dialogs. Install Python from python.org or the Microsoft Store to include Tk."

    def interpreter(self, environment: Path) -> Path:
        return environment.joinpath(*WINDOWS_INTERPRETER)

    def launcher(self, distribution: Path, *, release: bool) -> Path:
        if release:
            return distribution / BUNDLE_DIRECTORY / WINDOWS_LAUNCHER

        return distribution / WINDOWS_LAUNCHER

    def missing_package_manager(self) -> Optional[str]:
        return None

    def system_packages(self) -> Sequence[Sequence[str]]:
        return ()

    def build_environment(self, *, machine: str, portaudio_prefix: str) -> Sequence[str]:
        del machine, portaudio_prefix
        return ()
