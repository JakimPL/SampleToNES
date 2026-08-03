import gzip
import json
from pathlib import Path
from typing import Any, Dict, Final, List

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.formats.bitphase.btp import project_to_bytes, write_btp
from sampletones_core.formats.bitphase.builder import sample_to_bitphase
from sampletones_core.formats.bitphase.model.project import BitphaseProject
from sampletones_core.formats.bitphase.specification.chip import CHIP_TYPE_NES, TUNING_TABLE_LENGTH
from sampletones_core.paths import EXT_FILE_BITPHASE

from .conftest import build_features, build_instrument, build_sample

VOLUME_ENVELOPE: Final[List[int]] = [15, 10, 5, 0]
PITCH_CONTOUR: Final[List[int]] = [0, 3, 7, 12]

PROJECT_KEYS: Final[List[str]] = [
    "name",
    "author",
    "songs",
    "loopPointId",
    "patternOrder",
    "tables",
    "patternOrderColors",
    "instruments",
]
SONG_KEYS: Final[List[str]] = [
    "patterns",
    "tuningTable",
    "initialSpeed",
    "chipType",
    "chipVariant",
    "chipFrequency",
    "interruptFrequency",
    "a4TuningHz",
    "virtualChannelMap",
]
PATTERN_KEYS: Final[List[str]] = ["id", "length", "channels", "patternRows"]
ROW_KEYS: Final[List[str]] = ["note", "effects", "instrument", "table", "volume"]
INSTRUMENT_KEYS: Final[List[str]] = ["id", "chipType", "rows", "loop", "name"]
INSTRUMENT_ROW_KEYS: Final[List[str]] = [
    "pulseWidth",
    "volumeOrRate",
    "retrigger",
    "soundLength",
    "envelope",
    "toneAdd",
    "toneAccumulation",
    "sweep",
    "sweepRate",
    "sweepShift",
]
TABLE_KEYS: Final[List[str]] = ["id", "rows", "loop", "name"]


@pytest.fixture(name="project")
def project_fixture() -> BitphaseProject:
    return sample_to_bitphase(
        build_sample(
            "Kick",
            build_instrument("Kick Pulse 1", build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR)),
            build_instrument(
                "Kick Noise",
                build_features(VOLUME_ENVELOPE, duty_cycle=[1, 1, 0, 0]),
                generator=GeneratorName.NOISE,
            ),
        )
    )


@pytest.fixture(name="document")
def document_fixture(project: BitphaseProject) -> Dict[str, Any]:
    return json.loads(gzip.decompress(project_to_bytes(project)))


class TestTheFileIsGzippedJson:
    def test_the_bytes_decompress_to_json(self, document: Dict[str, Any]) -> None:
        assert isinstance(document, dict)

    def test_writing_the_same_document_twice_yields_the_same_bytes(self, project: BitphaseProject) -> None:
        """A fixed timestamp keeps the gzip header stable, so an unchanged document
        exports byte-identically and a diff shows only real changes.
        """
        assert project_to_bytes(project) == project_to_bytes(project)

    def test_the_file_lands_on_disk(self, project: BitphaseProject, tmp_path: Path) -> None:
        destination = tmp_path / f"Kick{EXT_FILE_BITPHASE}"
        write_btp(destination, project)
        assert json.loads(gzip.decompress(destination.read_bytes()))["name"] == "Kick"


class TestTheDocumentCarriesEveryFieldBitphaseReads:
    """Bitphase reconstructs a project field by field, falling back to a default for
    each one it misses, so a document holding every field loads as it was written.
    """

    @pytest.mark.parametrize("key", PROJECT_KEYS)
    def test_the_project_holds_its_field(self, document: Dict[str, Any], key: str) -> None:
        assert key in document

    @pytest.mark.parametrize("key", SONG_KEYS)
    def test_the_song_holds_its_field(self, document: Dict[str, Any], key: str) -> None:
        assert key in document["songs"][0]

    @pytest.mark.parametrize("key", PATTERN_KEYS)
    def test_the_pattern_holds_its_field(self, document: Dict[str, Any], key: str) -> None:
        assert key in document["songs"][0]["patterns"][0]

    @pytest.mark.parametrize("key", ROW_KEYS)
    def test_the_row_holds_its_field(self, document: Dict[str, Any], key: str) -> None:
        assert key in document["songs"][0]["patterns"][0]["channels"][0]["rows"][0]

    @pytest.mark.parametrize("key", INSTRUMENT_KEYS)
    def test_the_instrument_holds_its_field(self, document: Dict[str, Any], key: str) -> None:
        assert key in document["instruments"][0]

    @pytest.mark.parametrize("key", INSTRUMENT_ROW_KEYS)
    def test_the_instrument_row_holds_its_field(self, document: Dict[str, Any], key: str) -> None:
        assert key in document["instruments"][0]["rows"][0]

    @pytest.mark.parametrize("key", TABLE_KEYS)
    def test_the_table_holds_its_field(self, document: Dict[str, Any], key: str) -> None:
        assert key in document["tables"][0]

    def test_a_note_names_a_semitone_and_an_octave(self, document: Dict[str, Any]) -> None:
        note = document["songs"][0]["patterns"][0]["channels"][0]["rows"][0]["note"]
        assert set(note) == {"name", "octave"}

    def test_a_channel_names_the_channel_it_drives(self, document: Dict[str, Any]) -> None:
        channel = document["songs"][0]["patterns"][0]["channels"][0]
        assert set(channel) == {"rows", "label"}


class TestTheDocumentReadsAsNes:
    def test_the_song_names_the_chip(self, document: Dict[str, Any]) -> None:
        assert document["songs"][0]["chipType"] == CHIP_TYPE_NES

    def test_every_instrument_names_the_chip(self, document: Dict[str, Any]) -> None:
        assert {instrument["chipType"] for instrument in document["instruments"]} == {CHIP_TYPE_NES}

    def test_the_tuning_table_covers_every_note_index(self, document: Dict[str, Any]) -> None:
        assert len(document["songs"][0]["tuningTable"]) == TUNING_TABLE_LENGTH

    def test_the_order_names_patterns_the_song_holds(self, document: Dict[str, Any]) -> None:
        held = {pattern["id"] for pattern in document["songs"][0]["patterns"]}
        assert set(document["patternOrder"]) <= held


class TestTheEnvelopesSurvive:
    def test_the_volume_envelope_crosses_over_whole(self, document: Dict[str, Any]) -> None:
        rows = document["instruments"][0]["rows"]
        assert [row["volumeOrRate"] for row in rows] == VOLUME_ENVELOPE

    def test_the_pitch_contour_crosses_over_whole(self, document: Dict[str, Any]) -> None:
        assert document["tables"][0]["rows"] == PITCH_CONTOUR

    def test_the_noise_mode_reaches_the_waveform_field(self, document: Dict[str, Any]) -> None:
        rows = document["instruments"][1]["rows"]
        assert [row["pulseWidth"] for row in rows] == [1, 1, 0, 0]

    def test_the_rows_read_their_level_as_a_literal_volume(self, document: Dict[str, Any]) -> None:
        rows = document["instruments"][0]["rows"]
        assert all(row["envelope"] is False for row in rows)

    def test_the_rows_hold_the_note_for_as_long_as_the_envelope_runs(self, document: Dict[str, Any]) -> None:
        rows = document["instruments"][0]["rows"]
        assert all(row["soundLength"] == 0 for row in rows)
