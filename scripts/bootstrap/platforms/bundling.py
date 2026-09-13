from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Bundling:
    """What building a standalone bundle takes on one system.

    Attributes:
        icon: The icon file the bundle is stamped with, relative to the repository.
        executable_suffix: What the launcher's file name ends with.
        pyaudio_advice: How to supply PortAudio to the build interpreter.
        tkinter_advice: How to supply Tk to the build interpreter for a release bundle.
        tkinter_warning: What a development bundle built without Tk does about file dialogs.
    """

    icon: str
    executable_suffix: str
    pyaudio_advice: str
    tkinter_advice: str
    tkinter_warning: str

    def launcher(self, distribution: Path, *, name: str, release: bool) -> Path:
        """The executable PyInstaller writes under ``distribution``.

        Args:
            distribution: The directory the bundle is written into.
            name: The bundle's name.
            release: Whether the bundle is a release, which is a directory beside its launcher.

        Returns:
            Path: The launcher.
        """
        executable = f"{name}{self.executable_suffix}"
        if release:
            return distribution / name / executable

        return distribution / executable
