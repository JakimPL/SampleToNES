import csv
from math import ceil
from typing import Dict, List, Tuple

import pytest

from sampletones_player.compression.decode import decode_planes
from sampletones_player.compression.planes.rebuild import streams_from_planes
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.compression import MAX_LITERAL_BYTES
from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_shared.utils.tables import Table
from sampletones_tools.codec.report import session
from sampletones_tools.codec.report.corpus import LONG_ARRANGEMENT
from sampletones_tools.codec.report.encoding import (
    LITERALS,
    PLANE_VARIANTS,
    RECORDS,
    REGISTER_PLANES,
    SEARCH,
    SPLIT_CONTROL,
    Encoding,
)
from sampletones_tools.codec.report.session import CompressionReport, run_report
from sampletones_tools.codec.report.songs import available_bytes
from sampletones_tools.corpus.build import Corpus


@pytest.fixture(scope="module")
def report(synthetic_corpus: Corpus, tmp_path_factory: pytest.TempPathFactory) -> CompressionReport:
    """The report ``codec report`` writes, over the session's corpus in place of a build of its own."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(session, "build_synthetic_corpus", lambda: synthetic_corpus)
        return run_report(tmp_path_factory.mktemp("compression_report"))


@pytest.fixture(scope="module")
def encodings(report: CompressionReport) -> Tuple[Encoding, ...]:
    """Every corpus song compressed under every variant of the codec."""
    return report.encodings


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

    def test_every_layer_undercuts_a_record_per_tick(
        self,
        encodings: Tuple[Encoding, ...],
    ) -> None:
        """The pitch table is paid once, so what a song's own data is held against is the records.

        A tone channel writes three planes and three registers, and the noise channel two of
        each, so spelling every plane out reaches a record per tick and the opcodes counting the
        runs. The layers are what buy a song its room, and each of them undercuts the record by
        several times over.
        """
        for encoding in encodings:
            if encoding.variant == LITERALS:
                continue

            assert encoding.compressed.size < encoding.entry.records


class TestTheReportStatesWhatEachLayerSaves:
    """The measurements the format's constants are settled from."""

    def test_the_report_holds_the_baselines_then_every_variant_per_song(self, report: CompressionReport) -> None:
        with report.csv_path.open(encoding="utf-8", newline="") as handle:
            header, *rows = list(csv.reader(handle))

        variants: Dict[str, List[str]] = {}
        for row in rows:
            variants.setdefault(row[header.index("corpus")], []).append(row[header.index("variant")])

        assert list(variants) == [entry.name for entry in report.entries]
        assert all(
            listed == [RECORDS, REGISTER_PLANES, SPLIT_CONTROL, *(name for name, _ in PLANE_VARIANTS)]
            for listed in variants.values()
        )
        table = Table(columns=tuple(header), rows=tuple(tuple(row) for row in rows)).markdown_lines()
        document = report.markdown_path.read_text(encoding="utf-8").splitlines()
        assert document[document.index(table[0]) : document.index(table[0]) + len(table)] == table
