import struct

import pytest

from sampletones_core.formats.famitracker.binary import FamiTrackerWriter
from sampletones_core.formats.famitracker.specification.blocks import (
    BLOCK_NAME_LENGTH,
    Block,
)


class TestBlockFraming:
    def test_block_name_padded_to_fixed_length(self) -> None:
        writer = FamiTrackerWriter()
        with writer.block(Block("PARAMS", 6)):
            pass
        assert writer.data[:BLOCK_NAME_LENGTH] == b"PARAMS".ljust(BLOCK_NAME_LENGTH, b"\x00")

    def test_block_header_carries_version_and_size(self) -> None:
        writer = FamiTrackerWriter()
        with writer.block(Block("INFO", 1)) as body:
            body.write_uint8(7)
            body.write_uint8(9)
        version = struct.unpack_from("<i", writer.data, BLOCK_NAME_LENGTH)[0]
        size = struct.unpack_from("<i", writer.data, BLOCK_NAME_LENGTH + 4)[0]
        assert version == 1
        assert size == 2

    def test_block_payload_follows_header(self) -> None:
        writer = FamiTrackerWriter()
        with writer.block(Block("INFO", 1)) as body:
            body.write_uint8(7)
            body.write_uint8(9)
        payload_offset = BLOCK_NAME_LENGTH + 8
        assert writer.data[payload_offset:] == b"\x07\x09"

    def test_a_nested_block_frames_inside_its_parent(self) -> None:
        writer = FamiTrackerWriter()
        with writer.block(Block("INFO", 1)) as body:
            with body.block(Block("PARAMS", 2)) as inner:
                inner.write_uint8(7)
        size = struct.unpack_from("<i", writer.data, BLOCK_NAME_LENGTH + 4)[0]
        assert size == BLOCK_NAME_LENGTH + 9

    def test_block_name_exceeding_limit_raises(self) -> None:
        writer = FamiTrackerWriter()
        with pytest.raises(ValueError):
            with writer.block(Block("N" * (BLOCK_NAME_LENGTH + 1), 1)):
                pass
