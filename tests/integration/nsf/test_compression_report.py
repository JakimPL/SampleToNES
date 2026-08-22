from dataclasses import dataclass
from math import ceil
from pathlib import Path
from time import process_time
from typing import Dict, Final, List, Optional, Sequence, Tuple

import pytest

from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.decode import decode_planes
from sampletones_player.compression.dictionary.table import phrase_table
from sampletones_player.compression.encode import STREAM_START, encode_planes
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.plane import parse_plane
from sampletones_player.compression.planes.rebuild import streams_from_planes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.driver.image import DriverImage
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.specification.compression import (
    MAX_LITERAL_BYTES,
    PLANE_COUNT,
    PLANE_STATE_SIZE,
)
from sampletones_player.specification.registers import DUTY_CYCLE_SHIFT
from sampletones_player.specification.song import SONG_HEADER_SIZE
from tests.integration.nsf.corpus import LONG_ARRANGEMENT, CorpusEntry, build_corpus
from tests.integration.nsf.report import ReportRow, write_csv, write_markdown
from tests.integration.nsf.songs import available_bytes
from tests.integration.output import resolve_output_directory, resolve_output_path
from tests.integration.paths import COMPRESSION_OUTPUT_ENV

LITERALS: Final[str] = "literals"
HOLDS: Final[str] = "holds"
SEARCH: Final[str] = "search"
RECORDS: Final[str] = "records"
REGISTER_PLANES: Final[str] = "register planes"
SPLIT_CONTROL: Final[str] = "split control"
CONTROL_LEVEL_MASK: Final[int] = 0x3F

PLANE_VARIANTS: Final[Tuple[Tuple[str, CodecOptions], ...]] = (
    (LITERALS, CodecOptions(holds=False, phrases=False, transposition=False, search=False)),
    (HOLDS, CodecOptions(holds=True, phrases=False, transposition=False, search=False)),
    ("instruments", CodecOptions(holds=True, phrases=True, transposition=False, search=False)),
    ("transposition", CodecOptions(holds=True, phrases=True, transposition=True, search=False)),
    (SEARCH, CodecOptions(holds=True, phrases=True, transposition=True, search=True)),
)

CSV_FILENAME: Final[str] = "report.csv"
MARKDOWN_FILENAME: Final[str] = "report.md"


@dataclass(frozen=True)
class Encoding:
    """One corpus song compressed under one variant of the codec."""

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


def _register_planes(streams: ChannelStreams) -> Tuple[bytes, ...]:
    return tuple(
        bytes(tick.values[register] for tick in stream)
        for stream in streams.padded
        for register in range(len(stream[0].values))
    )


def _split_control_planes(planes: SongPlanes) -> Tuple[bytes, ...]:
    split: List[bytes] = []
    for channels in planes.ordered:
        if channels in (planes.pulse1, planes.pulse2):
            split.append(bytes(control >> DUTY_CYCLE_SHIFT for control in channels.control))
            split.append(bytes(control & CONTROL_LEVEL_MASK for control in channels.control))
        else:
            split.append(channels.control)

        split.append(channels.value)

    return tuple(split)


def _coded_size(planes: Sequence[bytes], options: CodecOptions) -> int:
    matcher = PhraseMatcher(phrase_table(()))
    entries = frozenset({STREAM_START})
    return sum(
        parse_plane(
            PlaneIndex.from_plane(plane),
            matcher,
            options,
            entries,
        ).size
        for plane in planes
    )


@pytest.fixture(scope="module")
def corpus(
    instrument_catalog: Dict[str, Sample],
    integration_project: Project,
) -> Tuple[CorpusEntry, ...]:
    """The songs the report measures: each sample alone, and the arrangement at two lengths."""
    return build_corpus(instrument_catalog, integration_project)


@pytest.fixture(scope="module")
def encodings(corpus: Tuple[CorpusEntry, ...]) -> Tuple[Encoding, ...]:
    """Every corpus song compressed under every variant of the codec."""
    encoded: List[Encoding] = []
    for entry in corpus:
        planes = entry.planes
        for variant, options in PLANE_VARIANTS:
            started = process_time()
            compressed = encode_planes(
                planes,
                entry.seeds,
                options=options,
                boundaries=frozenset(),
            )
            encoded.append(
                Encoding(
                    entry=entry,
                    variant=variant,
                    planes=planes,
                    compressed=compressed,
                    seconds=process_time() - started,
                )
            )

    return tuple(encoded)


def _measured_row(
    entry: CorpusEntry,
    variant: str,
    planes: Sequence[bytes],
    fixed: int,
    space: int,
) -> ReportRow:
    _, holds = PLANE_VARIANTS[1]
    started = process_time()
    coded = _coded_size(planes, holds)
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
        _measured_row(entry, REGISTER_PLANES, _register_planes(entry.song.streams), 0, space),
        _measured_row(
            entry,
            SPLIT_CONTROL,
            _split_control_planes(entry.planes),
            len(entry.pitches.data),
            space,
        ),
    )


def _rows(
    corpus: Sequence[CorpusEntry],
    encodings: Sequence[Encoding],
    space: int,
) -> Tuple[ReportRow, ...]:
    rows: List[ReportRow] = []
    for entry in corpus:
        rows.extend(_baseline_rows(entry, space))
        for encoding in encodings:
            if encoding.entry is not entry:
                continue

            rows.append(
                ReportRow(
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
            )

    return tuple(rows)


class TestTheCodecAnswersWithTheSongItWasGiven:
    """What the encoder writes, the decoder plays back, whichever layers are switched on."""

    def test_every_encoding_plays_back_as_the_planes_it_was_written_from(
        self,
        encodings: Tuple[Encoding, ...],
    ) -> None:
        for encoding in encodings:
            assert decode_planes(encoding.compressed) == encoding.planes

    def test_every_encoding_reaches_the_registers_the_song_writes(
        self,
        encodings: Tuple[Encoding, ...],
    ) -> None:
        """The planes are a reading of the streams, so playing them back writes the same registers."""
        for encoding in encodings:
            played = streams_from_planes(decode_planes(encoding.compressed), encoding.entry.pitches)
            written = encoding.entry.song.streams
            assert [played.at(tick) for tick in range(written.ticks)] == [
                written.at(tick) for tick in range(written.ticks)
            ]

    def test_a_plane_the_codec_finds_nothing_in_stays_within_its_literal_bound(
        self,
        encodings: Tuple[Encoding, ...],
    ) -> None:
        """With every layer switched off a plane costs its own bytes and one opcode per run of them."""
        for encoding in encodings:
            if encoding.variant != LITERALS:
                continue

            bound = encoding.compressed.ticks + ceil(encoding.compressed.ticks / MAX_LITERAL_BYTES)
            for stream in encoding.compressed.streams:
                assert len(stream) <= bound


class TestTheProgramAreaHoldsAWholeSong:
    """What the compression is for: an arrangement of minutes rather than seconds."""

    def test_a_three_minute_arrangement_fits_the_program_area(
        self,
        encodings: Tuple[Encoding, ...],
        driver_image: DriverImage,
    ) -> None:
        searched = [
            encoding for encoding in encodings if encoding.entry.name == LONG_ARRANGEMENT and encoding.variant == SEARCH
        ]
        assert searched
        assert SONG_HEADER_SIZE + searched[0].size <= available_bytes(driver_image)

    def test_every_variant_of_every_song_undercuts_a_record_per_tick(
        self,
        encodings: Tuple[Encoding, ...],
    ) -> None:
        """The pitch table is paid once, so what a song's own data is held against is the records."""
        for encoding in encodings:
            assert encoding.compressed.size < encoding.entry.records


class TestTheReportStatesWhatEachLayerSaves:
    """The measurements the format's constants are settled from."""

    def test_the_report_is_written(
        self,
        corpus: Tuple[CorpusEntry, ...],
        encodings: Tuple[Encoding, ...],
        driver_image: DriverImage,
        compression_output_dir: Optional[Path],
        tmp_path: Path,
    ) -> None:
        rows = _rows(corpus, encodings, available_bytes(driver_image))
        csv_path = resolve_output_path(compression_output_dir, tmp_path, CSV_FILENAME)
        markdown_path = resolve_output_path(compression_output_dir, tmp_path, MARKDOWN_FILENAME)
        write_csv(rows, csv_path)
        write_markdown(rows, markdown_path, PLANE_COUNT * PLANE_STATE_SIZE)
        assert csv_path.read_text(encoding="utf-8").count("\n") == len(rows) + 1
        assert markdown_path.exists()


@pytest.fixture(scope="session")
def compression_output_dir() -> Optional[Path]:
    """The persistent output directory ``SAMPLETONES_COMPRESSION_OUTPUT_DIR`` names."""
    return resolve_output_directory(COMPRESSION_OUTPUT_ENV)
