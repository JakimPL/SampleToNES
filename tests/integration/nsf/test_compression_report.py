from math import ceil
from pathlib import Path
from typing import Dict, Tuple

import pytest

from sampletones_core.project.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_player.compression.decode import decode_planes
from sampletones_player.compression.planes.rebuild import streams_from_planes
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.compression import MAX_LITERAL_BYTES
from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_tools.codec.report.corpus import LONG_ARRANGEMENT, CorpusEntry, corpus_entries
from sampletones_tools.codec.report.encoding import (
    LITERALS,
    SEARCH,
    Encoding,
    encode_corpus,
    report_rows,
)
from sampletones_tools.codec.report.session import write_report
from sampletones_tools.codec.report.songs import available_bytes


@pytest.fixture(scope="module")
def corpus(
    instrument_catalog: Dict[str, Sample],
    integration_project: Project,
) -> Tuple[CorpusEntry, ...]:
    """The songs the report measures: each sample alone, the arrangement at two lengths, and a dense minute."""
    return corpus_entries(instrument_catalog, integration_project)


@pytest.fixture(scope="module")
def encodings(corpus: Tuple[CorpusEntry, ...]) -> Tuple[Encoding, ...]:
    """Every corpus song compressed under every variant of the codec."""
    return encode_corpus(corpus)


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

    def test_the_report_is_written(
        self,
        corpus: Tuple[CorpusEntry, ...],
        encodings: Tuple[Encoding, ...],
        driver_image: DriverImage,
        tmp_path: Path,
    ) -> None:
        space = available_bytes(driver_image)
        csv_path, markdown_path = write_report(corpus, encodings, space, tmp_path)
        rows = report_rows(corpus, encodings, space)
        assert csv_path.read_text(encoding="utf-8").count("\n") == len(rows) + 1
        assert markdown_path.exists()
