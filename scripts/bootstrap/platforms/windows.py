from pathlib import Path
from typing import Dict, Final, Mapping, Optional, Sequence, Tuple

from bootstrap.platforms.bundling import Bundling

WINDOWS: Final[str] = "Windows"
WINDOWS_INTERPRETER: Final[Tuple[str, str]] = ("Scripts", "python.exe")
ICO_ICON: Final[str] = "src/sampletones_assets/icons/sampletones.ico"
EXECUTABLE_SUFFIX: Final[str] = ".exe"
NVIDIA_SMI_LOCATIONS: Final[Tuple[Tuple[str, str], ...]] = (
    ("SystemRoot", "System32/nvidia-smi.exe"),
    ("ProgramFiles", "NVIDIA Corporation/NVSMI/nvidia-smi.exe"),
)
BUNDLING: Final[Bundling] = Bundling(
    icon=ICO_ICON,
    executable_suffix=EXECUTABLE_SUFFIX,
    pyaudio_advice="Run install.bat from the project root to reinstall the dependencies.",
    tkinter_advice="Install Python from python.org or the Microsoft Store, which both include Tk, then build again.",
    tkinter_warning=(
        "This bundle opens no file dialogs. Install Python from python.org or the Microsoft Store to include Tk."
    ),
)


class Windows:
    """Windows: the official Python installer carries what the application needs.

    The NVIDIA driver installs ``nvidia-smi.exe`` into fixed system locations that ``PATH`` may
    leave out, so CUDA detection tries those too.
    """

    @property
    def name(self) -> str:
        return WINDOWS

    @property
    def cuda(self) -> bool:
        return True

    def interpreter(self, environment: Path) -> Path:
        return environment.joinpath(*WINDOWS_INTERPRETER)

    def bundling(self) -> Bundling:
        return BUNDLING

    def missing_package_manager(self) -> Optional[str]:
        return None

    def system_packages(self) -> Sequence[Sequence[str]]:
        return ()

    def setup_variables(self, base: Mapping[str, str], *, machine: str) -> Dict[str, str]:
        del machine
        return dict(base)

    def build_flags(self, *, machine: str) -> Sequence[str]:
        del machine
        return ()

    def nvidia_smi_locations(self, environment: Mapping[str, str]) -> Sequence[Path]:
        return tuple(
            Path(environment[variable]) / relative
            for variable, relative in NVIDIA_SMI_LOCATIONS
            if environment.get(variable)
        )
