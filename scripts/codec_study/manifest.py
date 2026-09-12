from __future__ import annotations

from pathlib import Path
from typing import Final, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.paths.user import PROJECTS_DIRECTORY, RECONSTRUCTIONS_DIRECTORY

PROJECT_SUFFIX: Final[str] = ".stp"
DEFAULT_PROJECT_NAMES: Final[Tuple[str, ...]] = ("Amen", "Demo", "Tempo", "Test")
QUICK_PROJECT_NAMES: Final[Tuple[str, ...]] = ("Test",)
LEAD_VOCALS: Final[str] = "lead-vocals"
DEFAULT_RECONSTRUCTIONS: Final[Tuple[Tuple[str, str], ...]] = (
    (
        LEAD_VOCALS,
        "sr_44100_nf_60_sm_cqt_tg_100_gn_p_ch_7376fe40aec68c41696a37cbf89baa55/0 Lead Vocals.stn",
    ),
    (
        "payoff-cqt",
        "sr_44100_nf_60_sm_cqt_tg_100_gn_PTN_ch_124286f3189248af752bf09c37323e5e/Payoff [Revenge A] Stems (123 BPM)",
    ),
    (
        "payoff-fft",
        "sr_44100_nf_60_sm_fft_tg_0_gn_PTN_ch_6d3be4658f9804463a01f2b34e3f0d16/Payoff [Revenge A] Stems (123 BPM)",
    ),
)


class StudySource(BaseModel):
    """One file or directory the corpus is read from.

    Attributes:
        label: What songs read from the source are called in a report.
        path: The file, or the directory whose stems are read.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    path: Path

    @classmethod
    def at(cls, path: Path) -> StudySource:
        """A source labeled by its own name: a file's stem, or a directory's name.

        Args:
            path: The file or directory.

        Returns:
            StudySource: The source under that label.
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

    @classmethod
    def load(cls, path: Path) -> StudyManifest:
        """Reads a manifest a run wrote, or one written by hand.

        Args:
            path: The manifest file, as JSON.

        Returns:
            StudyManifest: The manifest.
        """
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, path: Path) -> None:
        """Writes the manifest beside a run's report, so the run can be repeated.

        Args:
            path: Where the manifest is written, as JSON.
        """
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def default(
        cls,
        *,
        lengthen_seconds: int,
        variants: Tuple[str, ...],
        quick: bool,
    ) -> StudyManifest:
        """The corpus on this machine: the projects and stems the study is settled on.

        Args:
            lengthen_seconds: How long each project's lengthened copy lasts.
            variants: The names of the variants every song is encoded under.
            quick: Whether to read one small project and one stem, for a run that checks the
                harness rather than the codec.

        Returns:
            StudyManifest: The manifest.
        """
        project_names = QUICK_PROJECT_NAMES if quick else DEFAULT_PROJECT_NAMES
        reconstructions = tuple(
            StudySource(label=label, path=RECONSTRUCTIONS_DIRECTORY / relative)
            for label, relative in DEFAULT_RECONSTRUCTIONS
            if label == LEAD_VOCALS or not quick
        )
        return cls(
            projects=tuple(
                StudySource(label=name, path=PROJECTS_DIRECTORY / f"{name}{PROJECT_SUFFIX}") for name in project_names
            ),
            reconstructions=reconstructions,
            lengthen_seconds=lengthen_seconds,
            variants=variants,
        )
