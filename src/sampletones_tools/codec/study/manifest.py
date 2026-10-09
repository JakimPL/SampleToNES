from pathlib import Path
from typing import Final, Self, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

NAMES_A_SOURCE: Final[str] = "A study measures at least one project or reconstruction."


class StudySource(BaseModel):
    """One file or directory the corpus is read from.

    Attributes:
        label: What songs read from the source are called in a report.
        path: The file, or the directory whose stems are read.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    path: Path

    @model_validator(mode="after")
    def _names_a_file_or_directory(self) -> Self:
        """Raises:
        ValueError: If nothing stands at the path.
        """
        if not self.path.exists():
            raise ValueError(f"No file at {self.path}.")

        return self

    @classmethod
    def at(cls, path: Path) -> Self:
        """A source labeled by its own name: a file's stem, or a directory's name.

        Args:
            path: The file or directory.

        Returns:
            Self: The source under that label.
        """
        return cls(label=path.name if path.is_dir() else path.stem, path=path)


class StudyManifest(BaseModel):
    """What one run of the study reads and measures.

    Attributes:
        projects: The project files, each measured as it stands and at the lengthened duration.
        reconstructions: The stem files and directories of stems.
        lengthen_seconds: How long each project's lengthened copy lasts.
        variants: The names of the variants every song is encoded under.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    projects: Tuple[StudySource, ...]
    reconstructions: Tuple[StudySource, ...]
    lengthen_seconds: int = Field(ge=1)
    variants: Tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _names_a_source(self) -> Self:
        """Raises:
        ValueError: If the manifest names neither a project nor a reconstruction.
        """
        if not self.projects and not self.reconstructions:
            raise ValueError(NAMES_A_SOURCE)

        return self

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads a manifest a run wrote, or one written by hand.

        Args:
            path: The manifest file, as JSON.

        Returns:
            Self: The manifest.
        """
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, path: Path) -> None:
        """Writes the manifest beside a run's report, so the run can be repeated.

        Args:
            path: Where the manifest is written, as JSON.
        """
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
