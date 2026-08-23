from pathlib import Path
from typing import Optional

import numpy as np
import pytest

from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.formats.binary import BinaryWriter
from sampletones_core.formats.famitracker.instrument import (
    fti_bytes_to_instrument,
    instrument_to_fti_bytes,
    read_fti,
    write_fti,
)
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.sequences.features import (
    features_to_instrument_sequences,
)
from sampletones_core.formats.famitracker.specification.file import FTI_MAGIC, FTI_VERSION
from sampletones_core.formats.famitracker.specification.instruments import (
    EMPTY_DPCM_ASSIGNMENTS,
    EMPTY_DPCM_SAMPLES,
    INSTRUMENT_TYPE_2A03,
    STANDALONE_INSTRUMENT_INDEX,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    DEFAULT_SEQUENCE_SETTING,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    NO_RELEASE_POINT,
    SEQUENCE_COUNT_2A03,
    SEQUENCE_DISABLED,
    SEQUENCE_ENABLED,
    SequenceKind,
)
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_shared.exceptions import (
    IncompatibleInstrumentVersionError,
    InvalidInstrumentValuesError,
    MalformedInstrumentError,
    NotAnInstrumentFileError,
    UnsupportedInstrumentTypeError,
)

GOLDEN_INSTRUMENT_NAME = "Test Instrument"
GOLDEN_VOLUME = np.array([15, 12, 8, 0])
GOLDEN_ARPEGGIO = np.array([0, 2, -3])
GOLDEN_DUTY_CYCLE = np.array([0, 1])

GOLDEN_FTI_BYTES = (
    b"FTI2.4\x01\x0f\x00\x00\x00Test Instrument\x05"
    b"\x01\x04\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x0f\x0c\x08\x00"
    b"\x01\x03\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x02\xfd"
    b"\x00\x00"
    b"\x01\x02\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x01"
    b"\x00\x00\x00\x00\x00\x00\x00\x00"
)

SEQUENCE_COUNT_OFFSET = 26
TYPE_OFFSET = 6
SIGNATURE_LENGTH = 3


def fti_stating_volume_items(count: int) -> bytes:
    """A file whose volume sequence states ``count`` items, written field by field."""
    writer = BinaryWriter()
    writer.write_bytes(FTI_MAGIC)
    writer.write_bytes(FTI_VERSION)
    writer.write_uint8(INSTRUMENT_TYPE_2A03)
    writer.write_counted_string("Long")
    writer.write_int8(SEQUENCE_COUNT_2A03)
    writer.write_int8(SEQUENCE_ENABLED)
    writer.write_uint32(count)
    writer.write_int32(NO_LOOP_POINT)
    writer.write_int32(NO_RELEASE_POINT)
    writer.write_uint32(DEFAULT_SEQUENCE_SETTING)
    for _ in range(count):
        writer.write_int8(MAX_VOLUME)

    for _ in range(SEQUENCE_COUNT_2A03 - 1):
        writer.write_int8(SEQUENCE_DISABLED)

    writer.write_uint32(EMPTY_DPCM_ASSIGNMENTS)
    writer.write_uint32(EMPTY_DPCM_SAMPLES)
    return writer.data


def build_instrument(
    name: str,
    *,
    volume: np.ndarray,
    arpeggio: Optional[np.ndarray] = None,
    pitch: Optional[np.ndarray] = None,
    hi_pitch: Optional[np.ndarray] = None,
    duty_cycle: Optional[np.ndarray] = None,
    loop_point: Optional[int] = None,
    index: int = 0,
) -> Instrument2A03:
    sequences = features_to_instrument_sequences(
        volume=volume,
        arpeggio=arpeggio if arpeggio is not None else np.array([], dtype=int),
        pitch=pitch,
        hi_pitch=hi_pitch,
        duty_cycle=duty_cycle,
        loop_point=loop_point,
    )
    return Instrument2A03(index=index, name=name, sequences=sequences)


def golden_instrument() -> Instrument2A03:
    return build_instrument(
        GOLDEN_INSTRUMENT_NAME,
        volume=GOLDEN_VOLUME,
        arpeggio=GOLDEN_ARPEGGIO,
        duty_cycle=GOLDEN_DUTY_CYCLE,
    )


class TestWriteFtiGoldenBytes:
    """Pins the byte output so a change in the writer is caught. Each populated
    sequence carries the items its own envelope was written with, the shorter
    arpeggio and duty envelopes ending before the volume envelope does."""

    def test_output_matches_golden(self, tmp_path: Path) -> None:
        path = tmp_path / "golden.fti"
        write_fti(path, golden_instrument())
        assert path.read_bytes() == GOLDEN_FTI_BYTES


class TestReadGoldenBytes:
    """The reader takes the pinned bytes back into the instrument that wrote them."""

    def test_the_golden_bytes_read_back_as_the_instrument(self) -> None:
        assert fti_bytes_to_instrument(GOLDEN_FTI_BYTES) == golden_instrument()

    def test_the_name_comes_back(self) -> None:
        assert fti_bytes_to_instrument(GOLDEN_FTI_BYTES).name == GOLDEN_INSTRUMENT_NAME

    def test_a_standalone_file_holds_the_first_slot(self) -> None:
        assert fti_bytes_to_instrument(GOLDEN_FTI_BYTES).index == STANDALONE_INSTRUMENT_INDEX


class TestFtiRoundTrip:
    def test_the_bytes_come_back_the_same(self) -> None:
        instrument = golden_instrument()
        data = instrument_to_fti_bytes(instrument)
        assert instrument_to_fti_bytes(fti_bytes_to_instrument(data)) == data

    def test_the_name_round_trips(self) -> None:
        instrument = build_instrument("Bass Line", volume=np.array([15, 0]))
        assert fti_bytes_to_instrument(instrument_to_fti_bytes(instrument)).name == "Bass Line"

    def test_all_five_sequence_slots_are_present(self) -> None:
        instrument = fti_bytes_to_instrument(
            instrument_to_fti_bytes(build_instrument("Lead", volume=np.array([15, 0])))
        )
        assert set(instrument.sequences) == set(SequenceKind)

    def test_enabled_sequence_items_round_trip(self) -> None:
        instrument = build_instrument("Lead", volume=np.array([15, 12, 8, 0]), arpeggio=np.array([0, 2, -3]))
        read = fti_bytes_to_instrument(instrument_to_fti_bytes(instrument))
        assert read.sequences[SequenceKind.VOLUME].items == (15, 12, 8, 0)
        assert read.sequences[SequenceKind.ARPEGGIO].items == (0, 2, -3)

    def test_missing_sequences_come_back_disabled(self) -> None:
        instrument = fti_bytes_to_instrument(
            instrument_to_fti_bytes(build_instrument("Lead", volume=np.array([15, 0])))
        )
        assert not instrument.sequences[SequenceKind.PITCH].enabled
        assert not instrument.sequences[SequenceKind.HI_PITCH].enabled
        assert not instrument.sequences[SequenceKind.DUTY].enabled

    def test_the_loop_point_round_trips(self) -> None:
        instrument = build_instrument("Pad", volume=np.array([15, 10, 5]), loop_point=WHOLE_LOOP_POINT)
        read = fti_bytes_to_instrument(instrument_to_fti_bytes(instrument))
        assert read.sequences[SequenceKind.VOLUME].loop_point == WHOLE_LOOP_POINT

    def test_a_written_file_reads_back(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        instrument = golden_instrument()
        write_fti(path, instrument)
        assert read_fti(path) == instrument

    def test_a_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_fti(tmp_path / "absent.fti")


class TestReadFtiRefusals:
    def test_other_data_is_not_an_instrument_file(self) -> None:
        with pytest.raises(NotAnInstrumentFileError):
            fti_bytes_to_instrument(b"XXX" + GOLDEN_FTI_BYTES[SIGNATURE_LENGTH:])

    def test_another_layout_version_is_refused(self) -> None:
        with pytest.raises(IncompatibleInstrumentVersionError):
            fti_bytes_to_instrument(b"FTI9.9" + GOLDEN_FTI_BYTES[TYPE_OFFSET:])

    def test_the_refused_version_is_named(self) -> None:
        with pytest.raises(IncompatibleInstrumentVersionError) as raised:
            fti_bytes_to_instrument(b"FTI9.9" + GOLDEN_FTI_BYTES[TYPE_OFFSET:])

        assert raised.value.actual_version == "9.9"
        assert raised.value.expected_version == "2.4"

    def test_another_chip_is_refused(self) -> None:
        data = GOLDEN_FTI_BYTES[:TYPE_OFFSET] + b"\x05" + GOLDEN_FTI_BYTES[TYPE_OFFSET + 1 :]
        with pytest.raises(UnsupportedInstrumentTypeError):
            fti_bytes_to_instrument(data)

    def test_another_sequence_count_is_refused(self) -> None:
        data = GOLDEN_FTI_BYTES[:SEQUENCE_COUNT_OFFSET] + b"\x03" + GOLDEN_FTI_BYTES[SEQUENCE_COUNT_OFFSET + 1 :]
        with pytest.raises(MalformedInstrumentError):
            fti_bytes_to_instrument(data)

    def test_a_file_cut_short_is_refused(self) -> None:
        with pytest.raises(MalformedInstrumentError):
            fti_bytes_to_instrument(GOLDEN_FTI_BYTES[:20])

    def test_empty_data_is_refused(self) -> None:
        with pytest.raises(MalformedInstrumentError):
            fti_bytes_to_instrument(b"")

    def test_a_sequence_longer_than_one_holds_is_refused(self) -> None:
        with pytest.raises(InvalidInstrumentValuesError):
            fti_bytes_to_instrument(fti_stating_volume_items(MAX_SEQUENCE_ITEMS + 1))

    def test_a_sequence_of_the_length_one_holds_is_read(self) -> None:
        instrument = fti_bytes_to_instrument(fti_stating_volume_items(MAX_SEQUENCE_ITEMS))
        assert len(instrument.sequences[SequenceKind.VOLUME].items) == MAX_SEQUENCE_ITEMS

    def test_a_name_that_is_not_text_is_refused(self) -> None:
        data = GOLDEN_FTI_BYTES[:11] + b"\xff" * 15 + GOLDEN_FTI_BYTES[SEQUENCE_COUNT_OFFSET:]
        with pytest.raises(MalformedInstrumentError):
            fti_bytes_to_instrument(data)
