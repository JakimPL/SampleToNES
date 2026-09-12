from dataclasses import dataclass
from typing import Dict, Final, List, Tuple

from codec_study.accounting.coincident import coincident_starts
from codec_study.accounting.dictionary import default_counts, plateaus
from codec_study.accounting.finding import NOTHING, Finding
from codec_study.accounting.fixed import fixed_overheads
from codec_study.accounting.pairs import ramps_in_literals, set_holds
from codec_study.accounting.shares import PlaneShares, plane_shares
from codec_study.accounting.tokens import ReadToken, read_tokens
from codec_study.measure import Measurement
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.planes.order import PlaneOrder

HYPOTHESES: Final[Tuple[Tuple[str, str], ...]] = (
    ("H1", "hold chains"),
    ("H2", "plateaus in bodies"),
    ("H3", "set-then-hold"),
    ("H4", "default counts"),
    ("H5", "coincident starts"),
    ("H6", "ramps in literals"),
    ("H7", "fixed tables"),
)
LEADING_COLUMNS: Final[Tuple[str, ...]] = (
    "group",
    "song",
    "variant",
    "block",
    "dictionary",
    "streams",
    "hold opcodes",
    "literal opcodes",
    "literal payload",
    "phrase tokens",
    "idle planes",
    "idle bytes",
    "bend bytes",
)
COLUMNS: Final[Tuple[str, ...]] = (
    *LEADING_COLUMNS,
    *(f"{label} {column}" for label, _ in HYPOTHESES for column in ("targeted", "saving", "share")),
)


@dataclass(frozen=True)
class AccountingRow:
    """Where one encoding's bytes go, and what each hypothesis would reach in it.

    Attributes:
        group: Which kind of song it is.
        song: The song's name.
        variant: The variant the encoding was built by.
        block: The bytes the whole song block takes.
        dictionary: The bytes the dictionary takes.
        streams: The bytes the streams take together.
        planes: Every plane's shares, in the order the song block writes them.
        findings: What each hypothesis reaches, in the order of ``HYPOTHESES``.
    """

    group: str
    song: str
    variant: str
    block: int
    dictionary: int
    streams: int
    planes: Tuple[PlaneShares, ...]
    findings: Tuple[Finding, ...]

    @property
    def idle_planes(self) -> Tuple[PlaneShares, ...]:
        """The planes keeping one value throughout the song."""
        return tuple(plane for plane in self.planes if plane.idle)

    @property
    def cells(self) -> Tuple[str, ...]:
        """The row as the table prints it, column by column."""
        leading = (
            self.group,
            self.song,
            self.variant,
            f"{self.block}",
            f"{self.dictionary}",
            f"{self.streams}",
            f"{sum(plane.hold_opcodes for plane in self.planes)}",
            f"{sum(plane.literal_opcodes for plane in self.planes)}",
            f"{sum(plane.literal_payload for plane in self.planes)}",
            f"{sum(plane.phrase_bytes for plane in self.planes)}",
            f"{len(self.idle_planes)}",
            f"{sum(plane.stream for plane in self.idle_planes)}",
            f"{sum(plane.stream for plane in self.planes if plane.bend)}",
        )
        findings: List[str] = []
        for finding in self.findings:
            findings.extend((f"{finding.targeted}", f"{finding.saving}", self.share(finding.saving)))

        return (*leading, *findings)

    def share(self, saving: int) -> str:
        """``saving`` as a percentage of the whole block."""
        return f"{100.0 * saving / self.block:.1f}%"


def account(
    measurement: Measurement,
    compressed: CompressedPlanes,
) -> AccountingRow:
    """Reads one encoding back and states what every hypothesis would reach in it.

    Args:
        measurement: The encoding under the song and variant it belongs to.
        compressed: Its streams as the driver reads them.

    Returns:
        AccountingRow: The shares and the findings.
    """
    tokens: Dict[str, Tuple[ReadToken, ...]] = {
        name: read_tokens(stream) for name, stream in zip(PlaneOrder.names(), compressed.streams)
    }
    planes = tuple(
        plane_shares(name, plane, tokens[name])
        for name, plane in zip(PlaneOrder.names(), measurement.song.planes.planes)
    )
    every_token = [token for name in PlaneOrder.names() for token in tokens[name]]
    findings = (
        sum((plane.hold_chains for plane in planes), NOTHING),
        plateaus(compressed.phrases),
        sum((set_holds(tokens[name]) for name in PlaneOrder.names()), NOTHING),
        default_counts(compressed.phrases, every_token),
        coincident_starts(tokens),
        sum((ramps_in_literals(tokens[name]) for name in PlaneOrder.names()), NOTHING),
        fixed_overheads(measurement.song, compressed).finding,
    )
    return AccountingRow(
        group=measurement.song.group.value,
        song=measurement.song.name,
        variant=measurement.variant,
        block=measurement.block,
        dictionary=measurement.dictionary,
        streams=measurement.streams,
        planes=planes,
        findings=findings,
    )
