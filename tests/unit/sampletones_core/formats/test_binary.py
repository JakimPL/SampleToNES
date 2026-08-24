import struct
from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.formats.binary import BinaryReader, BinaryWriter
from sampletones_shared.exceptions import TruncatedDataError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestIntegerPrimitives(BaseTestSuite):
    """Each named write packs the width and signedness its name states."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: bytes
        method: str
        value: int

        @property
        def label(self) -> str:
            return f"{self.method}-{self.value}"

    test_cases: Tuple[TestCase, ...] = (
        TestCase(method="write_uint8", value=0, expected=b"\x00"),
        TestCase(method="write_uint8", value=255, expected=b"\xff"),
        TestCase(method="write_int8", value=-128, expected=b"\x80"),
        TestCase(method="write_int8", value=127, expected=b"\x7f"),
        TestCase(method="write_uint16", value=0, expected=b"\x00\x00"),
        TestCase(method="write_uint16", value=0x0440, expected=b"\x40\x04"),
        TestCase(method="write_uint16", value=65535, expected=b"\xff\xff"),
        TestCase(method="write_uint32", value=0x0440, expected=b"\x40\x04\x00\x00"),
        TestCase(method="write_uint32", value=4294967295, expected=b"\xff\xff\xff\xff"),
        TestCase(method="write_int32", value=-1, expected=b"\xff\xff\xff\xff"),
        TestCase(method="write_int32", value=2147483647, expected=b"\xff\xff\xff\x7f"),
    )

    @staticmethod
    def write(test_case: TestCase) -> BinaryWriter:
        writer = BinaryWriter()
        {
            "write_uint8": writer.write_uint8,
            "write_int8": writer.write_int8,
            "write_uint16": writer.write_uint16,
            "write_uint32": writer.write_uint32,
            "write_int32": writer.write_int32,
        }[test_case.method](test_case.value)
        return writer

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bytes_are_little_endian(self, test_case: TestCase) -> None:
        assert self.write(test_case).data == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_field_takes_the_width_its_name_states(self, test_case: TestCase) -> None:
        assert len(self.write(test_case)) == len(test_case.expected)

    def test_a_value_above_the_field_raises(self) -> None:
        writer = BinaryWriter()
        with pytest.raises(struct.error):
            writer.write_uint16(65536)

    def test_the_length_tracks_every_write(self) -> None:
        writer = BinaryWriter()
        writer.write_uint8(1)
        writer.write_uint16(2)
        writer.write_uint32(3)
        assert len(writer) == 7


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


class TestReadIntegerPrimitives(BaseTestSuite):
    """Each named read takes the width and signedness its name states, back off the writer."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        method: str

        @property
        def label(self) -> str:
            return f"{self.method}-{self.expected}"

    test_cases: Tuple[TestCase, ...] = (
        TestCase(method="uint8", expected=0),
        TestCase(method="uint8", expected=255),
        TestCase(method="int8", expected=-128),
        TestCase(method="int8", expected=127),
        TestCase(method="uint32", expected=0x0440),
        TestCase(method="uint32", expected=4294967295),
        TestCase(method="int32", expected=-1),
        TestCase(method="int32", expected=2147483647),
    )

    @staticmethod
    def written(test_case: TestCase) -> bytes:
        writer = BinaryWriter()
        {
            "uint8": writer.write_uint8,
            "int8": writer.write_int8,
            "uint32": writer.write_uint32,
            "int32": writer.write_int32,
        }[test_case.method](test_case.expected)
        return writer.data

    @staticmethod
    def read(reader: BinaryReader, method: str) -> int:
        return {
            "uint8": reader.read_uint8,
            "int8": reader.read_int8,
            "uint32": reader.read_uint32,
            "int32": reader.read_int32,
        }[method]()

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_value_comes_back_off_the_bytes(self, test_case: TestCase) -> None:
        reader = BinaryReader(self.written(test_case))
        assert self.read(reader, test_case.method) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_field_leaves_the_reader_at_the_end(self, test_case: TestCase) -> None:
        reader = BinaryReader(self.written(test_case))
        self.read(reader, test_case.method)
        assert reader.remaining == 0


class TestReadingAdvances:
    def test_each_read_takes_the_next_field(self) -> None:
        writer = BinaryWriter()
        writer.write_uint8(1)
        writer.write_uint32(2)
        writer.write_int32(-3)

        reader = BinaryReader(writer.data)
        assert (reader.read_uint8(), reader.read_uint32(), reader.read_int32()) == (1, 2, -3)

    def test_the_remainder_counts_down(self) -> None:
        reader = BinaryReader(b"\x01\x02\x03\x04")
        reader.read_uint8()
        assert reader.remaining == 3

    def test_read_bytes_takes_the_count_asked_for(self) -> None:
        reader = BinaryReader(b"abcdef")
        assert reader.read_bytes(3) == b"abc"
        assert reader.read_bytes(3) == b"def"

    def test_counted_string_round_trips(self) -> None:
        writer = BinaryWriter()
        writer.write_counted_string("Bass Line")
        assert BinaryReader(writer.data).read_counted_string() == "Bass Line"

    def test_counted_string_leaves_what_follows_it(self) -> None:
        writer = BinaryWriter()
        writer.write_counted_string("hi")
        writer.write_uint8(7)

        reader = BinaryReader(writer.data)
        reader.read_counted_string()
        assert reader.read_uint8() == 7


class TestReadingPastTheEnd:
    def test_a_field_wider_than_the_remainder_raises(self) -> None:
        reader = BinaryReader(b"\x01\x02")
        with pytest.raises(TruncatedDataError):
            reader.read_uint32()

    def test_more_bytes_than_held_raises(self) -> None:
        reader = BinaryReader(b"abc")
        with pytest.raises(TruncatedDataError):
            reader.read_bytes(4)

    def test_an_empty_buffer_raises_on_the_first_read(self) -> None:
        with pytest.raises(TruncatedDataError):
            BinaryReader(b"").read_uint8()

    def test_a_counted_string_longer_than_the_remainder_raises(self) -> None:
        writer = BinaryWriter()
        writer.write_uint32(10)
        writer.write_bytes(b"hi")
        with pytest.raises(TruncatedDataError):
            BinaryReader(writer.data).read_counted_string()

    def test_the_message_names_the_width_and_the_offset(self) -> None:
        reader = BinaryReader(b"\x01\x02")
        reader.read_uint8()
        with pytest.raises(TruncatedDataError, match="4 bytes at offset 1"):
            reader.read_uint32()
