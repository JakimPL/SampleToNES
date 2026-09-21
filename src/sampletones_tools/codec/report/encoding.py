from dataclasses import dataclass
from time import process_time
from typing import Final, List, Sequence, Tuple

from sampletones_core.constants.enums import PULSE_CHANNELS
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import phrase_table
from sampletones_player.compression.encode import STREAM_START, encode_planes
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.plane import parse_plane
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.specification.planes import PLANES, PlaneRole
from sampletones_player.specification.registers import DUTY_CYCLE_SHIFT
from sampletones_tools.codec.absent import is_absent
from sampletones_tools.codec.report.corpus import CorpusEntry
from sampletones_tools.codec.report.rows import ReportRow

LITERALS: Final[str] = "literals"
HOLDS: Final[str] = "holds"
INSTRUMENTS: Final[str] = "instruments"
TRANSPOSITION: Final[str] = "transposition"
SEARCH: Final[str] = "search"
RECORDS: Final[str] = "records"
REGISTER_PLANES: Final[str] = "register planes"
SPLIT_CONTROL: Final[str] = "split control"
CONTROL_LEVEL_MASK: Final[int] = 0x3F
HOLDS_OPTIONS: Final[CodecOptions] = CompressionScheme.RUNS.options

PLANE_VARIANTS: Final[Tuple[Tuple[str, CodecOptions], ...]] = (
    (LITERALS, CompressionScheme.NONE.options),
    (HOLDS, HOLDS_OPTIONS),
    (
        INSTRUMENTS,
        CodecOptions(
            holds=True,
            phrases=True,
            transposition=False,
            search=False,
        ),
    ),
    (TRANSPOSITION, CompressionScheme.INSTRUMENTS.options),
    (SEARCH, CompressionScheme.SEARCH.options),
)


@dataclass(frozen=True)
class Encoding:
    """One corpus song compressed under one variant of the codec.

    Attributes:
        entry: The song compressed.
        variant: The layers the codec was switched on with.
        planes: The planes the song separates into.
        compressed: What the encoder wrote.
        seconds: The processor time the encoding took.
    """

    entry: CorpusEntry
    variant: str
    planes: SongPlanes
    compressed: CompressedPlanes
    seconds: float

    @property
    def size(self) -> int:
        """The bytes the dictionary, the streams and the pitch table take together."""
        return self.compressed.size + len(self.entry.pitches.data)

    @property
    def streams(self) -> int:
        """The bytes the token streams take, which is the part that grows with the song."""
        return sum(len(stream) for stream in self.compressed.streams)


def encode_corpus(entries: Sequence[CorpusEntry]) -> Tuple[Encoding, ...]:
    """Compresses every corpus song under every variant of the codec, timing each encoding.

    Args:
        entries: The songs to compress.

    Returns:
        Tuple[Encoding, ...]: The encodings, song by song, each in the order of the variants.
    """
    encodings: List[Encoding] = []
    for entry in entries:
        planes = entry.planes
        for variant, options in PLANE_VARIANTS:
            started = process_time()
            compressed = encode_planes(
                planes,
                entry.seeds,
                options=options,
                boundaries=frozenset(),
            )
            encodings.append(
                Encoding(
                    entry=entry,
                    variant=variant,
                    planes=planes,
                    compressed=compressed,
                    seconds=process_time() - started,
                )
            )

    return tuple(encodings)


def report_rows(
    entries: Sequence[CorpusEntry],
    encodings: Sequence[Encoding],
    space: int,
) -> Tuple[ReportRow, ...]:
    """The report's measurements: per song, the baselines and then each of its encodings.

    Args:
        entries: The songs measured.
        encodings: Their encodings, as `encode_corpus` returns them.
        space: The program area a song is written into.

    Returns:
        Tuple[ReportRow, ...]: The rows, in the order the report prints them.
    """
    rows: List[ReportRow] = []
    for entry in entries:
        rows.extend(_baseline_rows(entry, space))
        rows.extend(_encoded_row(encoding, space) for encoding in encodings if encoding.entry is entry)

    return tuple(rows)


def _encoded_row(encoding: Encoding, space: int) -> ReportRow:
    entry = encoding.entry
    return ReportRow(
        corpus=entry.name,
        variant=encoding.variant,
        ticks=entry.song.ticks,
        size=encoding.size,
        variable=encoding.streams,
        phrases=len(encoding.compressed.phrases),
        dictionary=encoding.compressed.phrases.size,
        seconds=encoding.seconds,
        records=entry.records,
        space=space,
    )


def _baseline_rows(entry: CorpusEntry, space: int) -> Tuple[ReportRow, ...]:
    return (
        ReportRow(
            corpus=entry.name,
            variant=RECORDS,
            ticks=entry.song.ticks,
            size=entry.records,
            variable=entry.records,
            phrases=0,
            dictionary=0,
            seconds=0.0,
            records=entry.records,
            space=space,
        ),
        _measured_row(
            entry,
            REGISTER_PLANES,
            _register_planes(entry.song.streams),
            0,
            space,
        ),
        _measured_row(
            entry,
            SPLIT_CONTROL,
            _split_control_planes(entry.planes),
            len(entry.pitches.data),
            space,
        ),
    )


def _measured_row(
    entry: CorpusEntry,
    variant: str,
    planes: Sequence[bytes],
    fixed: int,
    space: int,
) -> ReportRow:
    started = process_time()
    coded = _coded_size(planes, HOLDS_OPTIONS)
    return ReportRow(
        corpus=entry.name,
        variant=variant,
        ticks=entry.song.ticks,
        size=fixed + coded,
        variable=coded,
        phrases=0,
        dictionary=0,
        seconds=process_time() - started,
        records=entry.records,
        space=space,
    )


def _register_planes(streams: ChannelStreams) -> Tuple[bytes, ...]:
    return tuple(
        bytes(tick.values[register] for tick in stream)
        for stream in streams.padded
        for register in range(len(stream[0].values))
    )


def _split_control_planes(planes: SongPlanes) -> Tuple[bytes, ...]:
    """Every plane with each pulse channel's control split into duty and volume."""
    split: List[bytes] = []
    for plane, played in zip(PLANES, planes.planes, strict=True):
        if plane.role is PlaneRole.CONTROL and plane.channel in PULSE_CHANNELS:
            split.append(bytes(control >> DUTY_CYCLE_SHIFT for control in played))
            split.append(bytes(control & CONTROL_LEVEL_MASK for control in played))
        else:
            split.append(played)

    return tuple(split)


def _coded_size(planes: Sequence[bytes], options: CodecOptions) -> int:
    """The bytes the planes take under holds and literals, an absent plane taking none."""
    present = [plane for plane in planes if not is_absent(plane)]
    cache = MatchCache(PlaneIndex.from_plane(plane) for plane in present)
    table = phrase_table(())
    entries = frozenset({STREAM_START})
    return sum(
        parse_plane(
            PhraseMatcher(table, plane, cache),
            options,
            entries,
        ).size
        for plane in range(len(present))
    )
