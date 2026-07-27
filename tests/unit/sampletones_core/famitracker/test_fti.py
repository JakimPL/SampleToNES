import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from sampletones_core.famitracker.fti import write_fti
from sampletones_core.famitracker.model.instrument import Instrument2A03
from sampletones_core.famitracker.sequences.features import features_to_instrument_sequences

GOLDEN_INSTRUMENT_NAME = "Test Instrument"
GOLDEN_VOLUME = np.array([15, 12, 8, 0])
GOLDEN_ARPEGGIO = np.array([0, 2, -3])
GOLDEN_DUTY_CYCLE = np.array([0, 1])

GOLDEN_FTI_BYTES = (
    b"FTI2.4\x01\x0f\x00\x00\x00Test Instrument\x05"
    b"\x01\x04\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x0f\x0c\x08\x00"
    b"\x01\x04\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x02\xfd\xfd"
    b"\x00\x00"
    b"\x01\x04\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x01\x01\x01"
    b"\x00\x00\x00\x00\x00\x00\x00\x00"
)


def build_instrument(
    name: str,
    *,
    volume: np.ndarray,
    arpeggio: Optional[np.ndarray] = None,
    pitch: Optional[np.ndarray] = None,
    hi_pitch: Optional[np.ndarray] = None,
    duty_cycle: Optional[np.ndarray] = None,
    loop: bool = False,
    index: int = 0,
) -> Instrument2A03:
    sequences = features_to_instrument_sequences(
        volume=volume,
        arpeggio=arpeggio if arpeggio is not None else np.array([], dtype=int),
        pitch=pitch,
        hi_pitch=hi_pitch,
        duty_cycle=duty_cycle,
        loop=loop,
    )
    return Instrument2A03(index=index, name=name, sequences=sequences)


@dataclass
class ParsedSequence:
    enabled: bool
    loop_point: int
    release_point: int
    setting: int
    items: List[int]


@dataclass
class ParsedFti:
    magic: bytes
    version: bytes
    instrument_type: int
    name: str
    sequences: List[ParsedSequence]
    dpcm_assignment_count: int
    dpcm_sample_count: int


def _read(data: bytes, offset: int, fmt: str) -> Tuple[int, int]:
    size = struct.calcsize(fmt)
    (value,) = struct.unpack_from(fmt, data, offset)
    return value, offset + size


def parse_fti(data: bytes) -> ParsedFti:
    offset = 0
    magic = data[offset : offset + 3]
    version = data[offset + 3 : offset + 6]
    offset += 6

    instrument_type, offset = _read(data, offset, "<B")
    name_length, offset = _read(data, offset, "<I")
    name = data[offset : offset + name_length].decode("utf-8")
    offset += name_length

    sequence_count, offset = _read(data, offset, "<b")
    sequences: List[ParsedSequence] = []
    for _ in range(sequence_count):
        enabled_flag, offset = _read(data, offset, "<b")
        if not enabled_flag:
            sequences.append(ParsedSequence(False, -1, -1, 0, []))
            continue

        length, offset = _read(data, offset, "<I")
        loop_point, offset = _read(data, offset, "<i")
        release_point, offset = _read(data, offset, "<i")
        setting, offset = _read(data, offset, "<I")
        items: List[int] = []
        for _ in range(length):
            item, offset = _read(data, offset, "<b")
            items.append(item)
        sequences.append(ParsedSequence(True, loop_point, release_point, setting, items))

    dpcm_assignment_count, offset = _read(data, offset, "<I")
    dpcm_sample_count, offset = _read(data, offset, "<I")

    return ParsedFti(
        magic=magic,
        version=version,
        instrument_type=instrument_type,
        name=name,
        sequences=sequences,
        dpcm_assignment_count=dpcm_assignment_count,
        dpcm_sample_count=dpcm_sample_count,
    )


class TestWriteFtiGoldenBytes:
    """Pins the byte output so a change in the writer is caught. Every populated
    sequence carries the same item count, the arpeggio and duty envelopes holding
    their final value through the volume envelope's trailing note-off item."""

    def test_output_matches_golden(self, tmp_path: Path) -> None:
        path = tmp_path / "golden.fti"
        instrument = build_instrument(
            GOLDEN_INSTRUMENT_NAME,
            volume=GOLDEN_VOLUME,
            arpeggio=GOLDEN_ARPEGGIO,
            duty_cycle=GOLDEN_DUTY_CYCLE,
        )
        write_fti(path, instrument)
        assert path.read_bytes() == GOLDEN_FTI_BYTES


class TestWriteFtiRoundTrip:
    def test_header_and_type(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        write_fti(path, build_instrument("Lead", volume=np.array([15, 0])))
        parsed = parse_fti(path.read_bytes())
        assert parsed.magic == b"FTI"
        assert parsed.version == b"2.4"
        assert parsed.instrument_type == 1

    def test_name_round_trips(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        write_fti(path, build_instrument("Bass Line", volume=np.array([15, 0])))
        parsed = parse_fti(path.read_bytes())
        assert parsed.name == "Bass Line"

    def test_all_five_sequence_slots_present(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        write_fti(path, build_instrument("Lead", volume=np.array([15, 0])))
        parsed = parse_fti(path.read_bytes())
        assert len(parsed.sequences) == 5

    def test_enabled_sequence_items_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        instrument = build_instrument("Lead", volume=np.array([15, 12, 8, 0]), arpeggio=np.array([0, 2, -3]))
        write_fti(path, instrument)
        parsed = parse_fti(path.read_bytes())
        assert parsed.sequences[0].enabled is True
        assert parsed.sequences[0].items == [15, 12, 8, 0]
        assert parsed.sequences[1].items == [0, 2, -3, -3]

    def test_missing_sequences_are_disabled(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        write_fti(path, build_instrument("Lead", volume=np.array([15, 0])))
        parsed = parse_fti(path.read_bytes())
        assert parsed.sequences[2].enabled is False
        assert parsed.sequences[3].enabled is False
        assert parsed.sequences[4].enabled is False

    def test_loop_flag_sets_loop_point(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        write_fti(path, build_instrument("Pad", volume=np.array([15, 10, 5]), loop=True))
        parsed = parse_fti(path.read_bytes())
        assert parsed.sequences[0].loop_point == 0

    def test_dpcm_section_is_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "instrument.fti"
        write_fti(path, build_instrument("Lead", volume=np.array([15, 0])))
        parsed = parse_fti(path.read_bytes())
        assert parsed.dpcm_assignment_count == 0
        assert parsed.dpcm_sample_count == 0
