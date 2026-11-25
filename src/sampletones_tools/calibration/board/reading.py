from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_shared.paths.extensions import EXT_FILE_JSON
from sampletones_tools.calibration.fingerprint import measured_variants
from sampletones_tools.calibration.layout import RENDERS_DIRECTORY
from sampletones_tools.calibration.referee.protocol import SCORE_READING
from sampletones_tools.calibration.renders import RenderRecord


class RunReading(BaseModel):
    """One calibration run as the page reads it: where it lies, what it measured, and what it recorded.

    Attributes:
        label: The name the page calls the run by, which is unique among the runs it holds.
        directory: The run directory every reference the page makes resolves against.
        measured: The labels of the variants the run measured, in the order it measured them.
        records: Every render the run wrote under the variants it measured, in the order the corpus
            generates its items.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    directory: Path
    measured: Tuple[str, ...]
    records: Tuple[RenderRecord, ...]

    @property
    def variants(self) -> Tuple[str, ...]:
        """The configurations the run measured and recorded, in the order they were measured.

        A run stopped before it reached a variant holds no record of it, so its page shows the
        variants it reached.
        """
        recorded = {record.variant for record in self.records}
        return tuple(variant for variant in self.measured if variant in recorded)

    @property
    def referee(self) -> str:
        """The referee whose score the page reports, which is the one the run's report leads with.

        Raises:
            ValueError: If the run recorded no judgment to read a referee from.
        """
        for record in self.records:
            for referee in record.judgments:
                return referee

        raise ValueError(f"Run '{self.directory}' recorded no judgment to read a referee from")

    def score(self, record: RenderRecord) -> float:
        """The headline referee's distance between a render and its recording."""
        return record.judgments[self.referee][SCORE_READING]

    def silence(self, record: RenderRecord) -> float:
        """The headline referee's distance between complete silence and the same recording."""
        return record.silence[self.referee]


def read_run(directory: Path, label: str) -> RunReading:
    """
    Read what a calibration run recorded, from the render records it wrote and its fingerprint.

    The records carry the scores, the categories and the frames each channel sounded, so a page is
    assembled from a finished run without repeating any measurement. The fingerprint lists the
    variants in the order the run measured them, which the page's columns follow, and the records of
    those variants alone are read.

    Args:
        directory: The run directory, the one holding ``renders`` and the fingerprint.
        label: The name the page calls the run by.

    Returns:
        The run's records, ordered by the corpus position they carry and then by variant.

    Raises:
        FileNotFoundError: If the directory holds no renders, or no fingerprint.
    """
    renders = directory / RENDERS_DIRECTORY
    paths = sorted(renders.glob(f"*/*{EXT_FILE_JSON}"))
    if not paths:
        raise FileNotFoundError(f"Directory '{directory}' holds no calibration renders to read")

    measured = measured_variants(directory)
    records = [RenderRecord.model_validate_json(path.read_text(encoding="utf-8")) for path in paths]
    held = [record for record in records if record.variant in measured]
    held.sort(key=lambda record: (record.position, record.variant))
    return RunReading(label=label, directory=directory, measured=measured, records=tuple(held))


def read_runs(directories: Sequence[Path]) -> Tuple[RunReading, ...]:
    """
    Read every run a page compares, each under a label of its own.

    A run is called by its directory's name, and a name two runs share is numbered, so every column
    the page draws names exactly one run.

    Args:
        directories: The run directories, in the order the page holds them.

    Returns:
        One reading per directory, in the order given.

    Raises:
        FileNotFoundError: If a directory holds no renders, or no fingerprint.
    """
    return tuple(read_run(directory, label) for directory, label in zip(directories, _labels(directories)))


def _labels(directories: Sequence[Path]) -> List[str]:
    taken: Dict[str, int] = {}
    labels: List[str] = []
    for directory in directories:
        name = directory.name
        taken[name] = taken.get(name, 0) + 1
        labels.append(name if taken[name] == 1 else f"{name} ({taken[name]})")

    return labels
