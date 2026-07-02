import struct
from dataclasses import dataclass
from typing import List

import pytest

from sampletones_core.famitracker.binary import BinaryWriter
from sampletones_core.famitracker.constants import BLOCK_NAME_LENGTH, Block


@dataclass
class IntegerCase:
    method: str
    format: str
    value: int


INTEGER_CASES: List[IntegerCase] = [
    IntegerCase("write_uint8", "<B", 0),
    IntegerCase("write_uint8", "<B", 255),
    IntegerCase("write_int8", "<b", -128),
    IntegerCase("write_int8", "<b", 127),
    IntegerCase("write_uint32", "<I", 0),
    IntegerCase("write_uint32", "<I", 0x0440),
    IntegerCase("write_uint32", "<I", 4294967295),
    IntegerCase("write_int32", "<i", -1),
    IntegerCase("write_int32", "<i", 2147483647),
]


class TestIntegerPrimitives:
    @pytest.mark.parametrize("case", INTEGER_CASES)
    def test_round_trips_via_struct(self, case: IntegerCase) -> None:
        writer = BinaryWriter()
        getattr(writer, case.method)(case.value)
        (unpacked,) = struct.unpack(case.format, writer.data)
        assert unpacked == case.value

    def test_writes_are_little_endian(self) -> None:
        writer = BinaryWriter()
        writer.write_uint32(0x0440)
        assert writer.data == b"\x40\x04\x00\x00"

    def test_length_tracks_written_bytes(self) -> None:
        writer = BinaryWriter()
        writer.write_uint8(1)
        writer.write_uint32(2)
        assert len(writer) == 5


class TestStringPrimitives:
    def test_fixed_string_pads_with_nul(self) -> None:
        writer = BinaryWriter()
        writer.write_fixed_string("abc", 8)
        assert writer.data == b"abc\x00\x00\x00\x00\x00"
        assert len(writer) == 8

    def test_fixed_string_truncates_to_length(self) -> None:
        writer = BinaryWriter()
        writer.write_fixed_string("abcdefgh", 4)
        assert writer.data == b"abcd"

    def test_counted_string_prefixes_length(self) -> None:
        writer = BinaryWriter()
        writer.write_counted_string("hi")
        length = struct.unpack_from("<I", writer.data, 0)[0]
        assert length == 2
        assert writer.data[4:] == b"hi"

    def test_terminated_string_appends_nul(self) -> None:
        writer = BinaryWriter()
        writer.write_terminated_string("note")
        assert writer.data == b"note\x00"


class TestBlockFraming:
    def test_block_name_padded_to_fixed_length(self) -> None:
        writer = BinaryWriter()
        with writer.block(Block("PARAMS", 6)):
            pass
        assert writer.data[:BLOCK_NAME_LENGTH] == b"PARAMS".ljust(BLOCK_NAME_LENGTH, b"\x00")

    def test_block_header_carries_version_and_size(self) -> None:
        writer = BinaryWriter()
        with writer.block(Block("INFO", 1)) as body:
            body.write_uint8(7)
            body.write_uint8(9)
        version = struct.unpack_from("<i", writer.data, BLOCK_NAME_LENGTH)[0]
        size = struct.unpack_from("<i", writer.data, BLOCK_NAME_LENGTH + 4)[0]
        assert version == 1
        assert size == 2

    def test_block_payload_follows_header(self) -> None:
        writer = BinaryWriter()
        with writer.block(Block("INFO", 1)) as body:
            body.write_uint8(7)
            body.write_uint8(9)
        payload_offset = BLOCK_NAME_LENGTH + 8
        assert writer.data[payload_offset:] == b"\x07\x09"

    def test_block_name_exceeding_limit_raises(self) -> None:
        writer = BinaryWriter()
        with pytest.raises(ValueError):
            with writer.block(Block("N" * (BLOCK_NAME_LENGTH + 1), 1)):
                pass
