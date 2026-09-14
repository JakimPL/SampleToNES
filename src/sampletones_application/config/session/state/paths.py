from pathlib import Path

from pydantic import BaseModel, Field, field_serializer

from sampletones_shared.paths.user import (
    CONFIG_PATH,
    LIBRARY_DIRECTORY,
    PROJECTS_DIRECTORY,
    RECONSTRUCTIONS_DIRECTORY,
)
from sampletones_shared.utils.system.paths import nearest_directory


class LastPaths(BaseModel):
    library: Path = Field(
        default=LIBRARY_DIRECTORY,
        description="The last used library directory path.",
    )
    reconstruction: Path = Field(
        default=RECONSTRUCTIONS_DIRECTORY,
        description="The last used directory of saved reconstruction files.",
    )
    audio_input: Path = Field(
        default=Path.home(),
        description="The last used directory of audio chosen for reconstruction.",
    )
    config: Path = Field(
        default=CONFIG_PATH.parent,
        description="The last used configuration file path.",
    )
    instrument: Path = Field(
        default=Path.cwd(),
        description="The last used FamiTracker instrument file path.",
    )
    audio: Path = Field(
        default=Path.cwd(),
        description="The last used WAV export file path.",
    )
    project: Path = Field(
        default=PROJECTS_DIRECTORY,
        description="The last used project directory path.",
    )

    @field_serializer(
        "library",
        "reconstruction",
        "audio_input",
        "config",
        "instrument",
        "audio",
        "project",
    )
    def serialize_paths(self, path: Path) -> str:
        return str(path)

    def relocate_missing(self) -> None:
        """Moves each remembered folder that has left the disk to the nearest folder standing above it.

        A dialog opens where the reader last worked, so a folder removed since opens it at the
        closest folder on the way there, and a folder on a drive that is gone opens it where a new
        profile would.
        """
        defaults = LastPaths()
        self.library = self._standing_directory(self.library, defaults.library)
        self.reconstruction = self._standing_directory(self.reconstruction, defaults.reconstruction)
        self.audio_input = self._standing_directory(self.audio_input, defaults.audio_input)
        self.config = self._standing_directory(self.config, defaults.config)
        self.instrument = self._standing_directory(self.instrument, defaults.instrument)
        self.audio = self._standing_directory(self.audio, defaults.audio)
        self.project = self._standing_directory(self.project, defaults.project)

    @staticmethod
    def _standing_directory(path: Path, default: Path) -> Path:
        directory = nearest_directory(path)
        if directory is None:
            return default

        return directory
