import hashlib
from pathlib import Path
from typing import Dict, Final, List, Sequence

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName

from .corpus.item import CorpusItem
from .runner import CalibrationVariant

FINGERPRINT_FILE: Final[str] = "run.json"


class ResumeRefusedError(ValueError):
    """Raised when a run directory holds no run, or a run measured otherwise than the one asked to resume it."""


class RunFingerprint(BaseModel):
    """What a run measures, which a run resuming it must measure alike.

    Attributes:
        variants: Each variant's label beside a digest of its configuration.
        channels: The channels the synthesized sounds are converted over.
        items: Each sound's name beside a digest of its family, category, listing and audio.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    variants: Dict[str, str]
    channels: List[str]
    items: Dict[str, str]


def fingerprint_of(
    variants: Sequence[CalibrationVariant],
    items: Sequence[CorpusItem],
    channels: Sequence[ChannelName],
) -> RunFingerprint:
    """The fingerprint of a run measuring ``items`` under ``variants`` over ``channels``."""
    return RunFingerprint(
        variants={variant.label: _digest(variant.config.model_dump_json().encode()) for variant in variants},
        channels=[channel.value for channel in channels],
        items={item.name: _item_digest(item) for item in items},
    )


def write_fingerprint(run_directory: Path, fingerprint: RunFingerprint) -> None:
    """Write the fingerprint of the run the directory holds."""
    run_directory.mkdir(parents=True, exist_ok=True)
    (run_directory / FINGERPRINT_FILE).write_text(fingerprint.model_dump_json(indent=1), encoding="utf-8")


def check_resumable(run_directory: Path, fingerprint: RunFingerprint) -> None:
    """Confirm the directory holds a run measuring what ``fingerprint`` measures.

    Raises:
        ResumeRefusedError: If the directory holds no fingerprint, or one that differs, naming what
            differs.
    """
    path = run_directory / FINGERPRINT_FILE
    if not path.is_file():
        raise ResumeRefusedError(f"'{run_directory}' holds no run to resume")

    recorded = RunFingerprint.model_validate_json(path.read_text(encoding="utf-8"))
    comparisons = (
        ("variants", recorded.variants == fingerprint.variants),
        ("channels", recorded.channels == fingerprint.channels),
        ("sounds", recorded.items == fingerprint.items),
    )
    differing = [name for name, alike in comparisons if not alike]
    if differing:
        named = ", ".join(differing)
        raise ResumeRefusedError(f"The run in '{run_directory}' measured other {named}; start a new run instead")


def _item_digest(item: CorpusItem) -> str:
    stems = item.stems.config.model_dump_json() if item.stems is not None else ""
    described = f"{item.family.value}|{item.category}|{item.listed}|{stems}".encode()
    return _digest(described + item.audio.tobytes())


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
