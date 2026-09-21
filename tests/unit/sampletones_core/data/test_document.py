from pathlib import Path
from typing import Final

import msgpack
import pytest

from sampletones_core.data.document import (
    DOCUMENT_MAGIC,
    compress_document,
    decompress_document,
    open_document,
)

RECORDS: Final[int] = 512
FIELD: Final[str] = "leading"


def _payload() -> bytes:
    """A payload of the shape a stored document holds: one map per record, keyed by name."""
    records = [{"on": index % 2 == 0, "pitch": 33, "volume": index % 16} for index in range(RECORDS)]
    return bytes(msgpack.packb({FIELD: "2.2", "records": records}, use_bin_type=True))


class TestWhatAStoredDocumentHolds:
    def test_a_payload_comes_back_as_it_was_written(self) -> None:
        payload = _payload()

        assert decompress_document(compress_document(payload)) == payload

    def test_a_payload_written_before_the_framing_reads_as_it_stands(self) -> None:
        payload = _payload()

        assert decompress_document(payload) == payload

    def test_the_stored_bytes_carry_the_framing_magic(self) -> None:
        assert compress_document(_payload()).startswith(DOCUMENT_MAGIC)

    def test_the_repeated_field_names_deflate_away(self) -> None:
        payload = _payload()

        assert len(compress_document(payload)) < len(payload)

    def test_storing_one_payload_twice_writes_the_same_bytes(self) -> None:
        """The framing states its timestamp, so a document's bytes follow from its payload alone."""
        payload = _payload()

        assert compress_document(payload) == compress_document(payload)

    def test_an_empty_payload_survives_the_round_trip(self) -> None:
        assert decompress_document(compress_document(b"")) == b""


class TestReadingADocumentAsAStream:
    def test_a_stored_document_streams_as_its_payload(self, tmp_path: Path) -> None:
        payload = _payload()
        path = tmp_path / "document.bin"
        path.write_bytes(compress_document(payload))

        with open_document(path) as stream:
            assert stream.read() == payload

    def test_a_document_written_before_the_framing_streams_as_it_stands(self, tmp_path: Path) -> None:
        payload = _payload()
        path = tmp_path / "document.bin"
        path.write_bytes(payload)

        with open_document(path) as stream:
            assert stream.read() == payload

    def test_the_stream_reaches_the_front_without_the_rest(self, tmp_path: Path) -> None:
        payload = _payload()
        path = tmp_path / "document.bin"
        path.write_bytes(compress_document(payload))

        with open_document(path) as stream:
            unpacker = msgpack.Unpacker(stream, raw=False)
            unpacker.read_map_header()

            assert unpacker.unpack() == FIELD

    def test_a_missing_document_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            with open_document(tmp_path / "absent.bin"):
                pass
