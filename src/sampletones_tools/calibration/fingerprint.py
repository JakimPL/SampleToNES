from pathlib import Path
from typing import Dict, Final, List, Optional, Self, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from sampletones_core.constants.enums import ChannelName, ordered_channels

from .corpus.item import CorpusItem
from .corpus.truth import Truth
from .digest import sha256_digest
from .layout import combination_name
from .referee.panel import RefereePanel
from .variants import CalibrationVariant

FINGERPRINT_FILE: Final[str] = "run.json"
FINGERPRINT_INDENT: Final[int] = 1
DESCRIPTION_SEPARATOR: Final[str] = "|"
NO_STEMS: Final[str] = ""
NO_CHANNELS: Final[str] = ""
TRUTH_ADAPTER: Final[TypeAdapter[Optional[Truth]]] = TypeAdapter(Optional[Truth])


class ResumeRefusedError(ValueError):
    """Raised when a run cannot claim its directory.

    A resumed run is refused a directory holding no run, or a run measured otherwise than the one asked
    to resume it. A fresh run is refused a directory holding renders or recordings no run claimed.
    """


class RunFingerprint(BaseModel):
    """What a run measures and what measures it, which a run resuming it must share.

    A resumed run reads back the records a run left and converts only the rest, so a record stands in
    for a conversion the resumed run would make itself only where the two runs share every part its
    readings depend on: the same configurations under the same labels, the same channels, the same
    sounds, the same referees under the same tuning, and the same program. Each variant and sound
    is held by a digest, so any change to a configuration's value, or to a sound's audio, family,
    category, listing, stems setup, own channels or truth, tells the runs apart. The channels are
    held in the order the application names them, since a conversion reads them as a set.

    The program is held by a digest of its source (``source_digest``) over the packages that make a
    record: ``sampletones_core`` converts, ``sampletones_tools`` builds the corpus, judges and writes
    the records, and ``sampletones_shared`` serves both. Their configuration files lie among their
    files, the generation defaults and the corpus and referee settings with them. An edit to any of
    them between two releases therefore tells the runs apart, as a release does.

    Attributes:
        variants: Each variant's label beside a digest of its configuration, in the order the run
            measures them.
        channels: The channels the synthesized sounds are converted over.
        items: Each sound's name beside a digest of what the corpus holds of it.
        referees: A digest of the referees' names and of the tuning they were built with.
        source: A digest of the program measuring the run: its version and its source.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    variants: Dict[str, str]
    channels: List[str]
    items: Dict[str, str]
    referees: str
    source: str

    def differences(self, other: Self) -> List[str]:
        """The parts ``other`` measures otherwise, named as a refusal names them.

        What the run is asked to measure comes first, then what measures it: the variants, the
        channels and the sounds, then the referees and the program's source.
        """
        comparisons = (
            ("variants", self.variants == other.variants),
            ("channels", self.channels == other.channels),
            ("sounds", self.items == other.items),
            ("referees", self.referees == other.referees),
            ("source code", self.source == other.source),
        )
        return [name for name, alike in comparisons if not alike]


class MeasuredVariants(BaseModel):
    """The part of a run's fingerprint a page reads: the variants the run measured, in its order.

    A page compares runs that different versions of the program measured, so it reads the one part
    every fingerprint holds and leaves the rest to a resume.

    Attributes:
        variants: Each variant's label beside a digest of its configuration, in the order the run
            measured them.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    variants: Dict[str, str]


def fingerprint_of(
    variants: Sequence[CalibrationVariant],
    items: Sequence[CorpusItem],
    channels: Sequence[ChannelName],
    panel: RefereePanel,
    source: str,
) -> RunFingerprint:
    """The fingerprint of a run measuring ``items`` under ``variants`` over ``channels``.

    The run is judged by ``panel`` and made by the program whose source digest is ``source``.
    """
    return RunFingerprint(
        variants={variant.label: sha256_digest(variant.config.model_dump_json().encode()) for variant in variants},
        channels=[channel.value for channel in ordered_channels(set(channels))],
        items={item.name: _item_digest(item) for item in items},
        referees=_referees_digest(panel),
        source=source,
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
        ResumeRefusedError: If the directory holds no fingerprint, one in a form this version cannot
            read, or one that differs, naming what differs.
    """
    if not holds_fingerprint(run_directory):
        raise ResumeRefusedError(f"'{run_directory}' holds no run to resume")

    text = (run_directory / FINGERPRINT_FILE).read_text(encoding="utf-8")
    recorded = _recorded_fingerprint(run_directory, text)
    differing = recorded.differences(fingerprint)
    if differing:
        named = ", ".join(differing)
        raise ResumeRefusedError(f"The run in '{run_directory}' measured other {named}; start a new run instead")


def holds_fingerprint(run_directory: Path) -> bool:
    """Whether a run claimed the directory, which its fingerprint there tells."""
    return (run_directory / FINGERPRINT_FILE).is_file()


def measured_variants(run_directory: Path) -> Tuple[str, ...]:
    """The labels of the variants the run in ``run_directory`` measured, in the order it measured them.

    Raises:
        FileNotFoundError: If the directory holds no fingerprint.
    """
    path = run_directory / FINGERPRINT_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Directory '{run_directory}' holds no {FINGERPRINT_FILE} naming its variants")

    return tuple(MeasuredVariants.model_validate_json(path.read_text(encoding="utf-8")).variants)


def _recorded_fingerprint(run_directory: Path, text: str) -> RunFingerprint:
    """The fingerprint ``text`` holds, read back from the run in ``run_directory``.

    Raises:
        ResumeRefusedError: If the text holds a fingerprint in a form this version cannot read, such as
            one an earlier version wrote.
    """
    try:
        return RunFingerprint.model_validate_json(text)
    except ValidationError as error:
        raise ResumeRefusedError(
            f"The run in '{run_directory}' records what it measured in a form this version cannot read; "
            "start a new run instead"
        ) from error


def _item_digest(item: CorpusItem) -> str:
    """The digest of a sound: its family, category, listing, stems setup, own channels and truth, then its audio."""
    stems = item.stems.config.model_dump_json() if item.stems is not None else NO_STEMS
    channels = combination_name(ordered_channels(item.channels)) if item.channels is not None else NO_CHANNELS
    truth = TRUTH_ADAPTER.dump_json(item.truth).decode()
    described = DESCRIPTION_SEPARATOR.join(
        (item.family.value, item.category, str(item.listed), stems, channels, truth)
    ).encode()
    return sha256_digest(described + item.audio.tobytes())


def _referees_digest(panel: RefereePanel) -> str:
    """The digest of a panel: its referees' names in the order they judge, then the tuning they share."""
    return sha256_digest(DESCRIPTION_SEPARATOR.join((*panel.names, panel.config.model_dump_json())).encode())
