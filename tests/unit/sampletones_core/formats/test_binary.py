import struct
from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.formats.binary import BinaryWriter
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
