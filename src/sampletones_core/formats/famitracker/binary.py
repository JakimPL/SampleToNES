from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sampletones_core.formats.binary import BinaryWriter
from sampletones_core.formats.famitracker.specification.blocks import BLOCK_NAME_LENGTH, Block


class FamiTrackerWriter(BinaryWriter):
    """A binary writer that frames the named, versioned blocks a FamiTracker module is built from."""

    @contextmanager
    def block(self, descriptor: Block) -> Iterator[FamiTrackerWriter]:
        """Frames a named, versioned block around a buffered payload.

        The payload written to the yielded writer is emitted with the block name
        (NUL-padded to :data:`BLOCK_NAME_LENGTH`), the version (``int32``) and the
        payload size (``int32``) in front of it, so the size is known before the
        header is written.
        """
        payload = FamiTrackerWriter()
        yield payload

        body = payload.data
        self._write_block_name(descriptor.name)
        self.write_int32(descriptor.version)
        self.write_int32(len(body))
        self.write_bytes(body)

    def _write_block_name(self, name: str) -> None:
        encoded = name.encode("ascii")
        if len(encoded) > BLOCK_NAME_LENGTH:
            raise ValueError(f"Block name '{name}' exceeds {BLOCK_NAME_LENGTH} bytes")

        self.write_bytes(encoded)
        self.write_bytes(b"\x00" * (BLOCK_NAME_LENGTH - len(encoded)))
