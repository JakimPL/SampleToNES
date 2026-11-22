from pathlib import Path
from typing import Dict, Final, List, Self, Sequence

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName

from .corpus.item import CorpusItem
from .digest import sha256_digest
from .variants import CalibrationVariant

FINGERPRINT_FILE: Final[str] = "run.json"
FINGERPRINT_INDENT: Final[int] = 1
DESCRIPTION_SEPARATOR: Final[str] = "|"
NO_STEMS: Final[str] = ""


class ResumeRefusedError(ValueError):
    """Raised when a run directory holds no run, or a run measured otherwise than the one asked to resume it."""


class RunFingerprint(BaseModel):
    """What a run measures, which a run resuming it must measure alike.

    A resumed run reads back the records a run left and converts only the rest, so a record stands in
    for a conversion the resumed run would make itself only where the two runs measure the same:
    the same configurations under the same labels, the same channels in the same order, and the same
    sounds. Each variant and sound is held by a digest, so any change to a configuration's value or a
    sound's audio, family, category, listing or stems setup tells the runs apart.

    Attributes:
        variants: Each variant's label beside a digest of its configuration.
        channels: The channels the synthesized sounds are converted over.
        items: Each sound's name beside a digest of its family, category, listing, stems setup and audio.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    variants: Dict[str, str]
    channels: List[str]
    items: Dict[str, str]

    def differences(self, other: Self) -> List[str]:
        """The parts ``other`` measures otherwise, named as a refusal names them, in a fixed order."""
        comparisons = (
            ("variants", self.variants == other.variants),
            ("channels", self.channels == other.channels),
            ("sounds", self.items == other.items),
        )
        return [name for name, alike in comparisons if not alike]


def fingerprint_of(
    variants: Sequence[CalibrationVariant],
    items: Sequence[CorpusItem],
    channels: Sequence[ChannelName],
) -> RunFingerprint:
    """The fingerprint of a run measuring ``items`` under ``variants`` over ``channels``."""
    return RunFingerprint(
        variants={variant.label: sha256_digest(variant.config.model_dump_json().encode()) for variant in variants},
        channels=[channel.value for channel in channels],
        items={item.name: _item_digest(item) for item in items},
    )


def write_fingerprint(run_directory: Path, fingerprint: RunFingerprint) -> None:
    """Write the fingerprint of the run the directory holds."""
    run_directory.mkdir(parents=True, exist_ok=True)
    (run_directory / FINGERPRINT_FILE).write_text(
        fingerprint.model_dump_json(indent=FINGERPRINT_INDENT), encoding="utf-8"
    )


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
    differing = recorded.differences(fingerprint)
    if differing:
        named = ", ".join(differing)
        raise ResumeRefusedError(f"The run in '{run_directory}' measured other {named}; start a new run instead")


def _item_digest(item: CorpusItem) -> str:
    """The digest of a sound: its family, category, listing and stems setup, then its audio's bytes."""
    stems = item.stems.config.model_dump_json() if item.stems is not None else NO_STEMS
    described = DESCRIPTION_SEPARATOR.join((item.family.value, item.category, str(item.listed), stems)).encode()
    return sha256_digest(described + item.audio.tobytes())
