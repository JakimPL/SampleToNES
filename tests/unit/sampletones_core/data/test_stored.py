from pathlib import Path
from typing import Final

import msgpack

from sampletones_core.data.document import compress_document
from sampletones_core.data.stored import read_leading_fields

LEADING: Final[str] = "leading"
FOLLOWING: Final[str] = "following"
TRAILING: Final[str] = "trailing"
HELD: Final[str] = "held"


def _stored(path: Path, payload: bytes) -> Path:
    path.write_bytes(payload)
    return path


class TestTheFieldsReadFromTheFront:
    def test_the_named_fields_read_as_stored(self, tmp_path: Path) -> None:
        document = {LEADING: {"version": "2.1"}, FOLLOWING: [1, 2], TRAILING: b"\x00" * 64}
        path = _stored(tmp_path / "document.bin", msgpack.packb(document, use_bin_type=True))

        fields = read_leading_fields(path, frozenset({LEADING, FOLLOWING}))

        assert fields == {LEADING: document[LEADING], FOLLOWING: document[FOLLOWING]}

    def test_a_field_the_document_holds_no_value_for_is_left_out(self, tmp_path: Path) -> None:
        path = _stored(tmp_path / "document.bin", msgpack.packb({LEADING: 1}, use_bin_type=True))

        assert read_leading_fields(path, frozenset({LEADING, HELD})) == {LEADING: 1}

    def test_the_read_ends_once_every_named_field_is_found(self, tmp_path: Path) -> None:
        """The fields past the named ones are left undecoded, so what stands there never matters."""
        front = b"".join(msgpack.packb(part, use_bin_type=True) for part in (LEADING, 1, FOLLOWING, 2))
        three_fields = b"\x83" + front + msgpack.packb(TRAILING) + b"\xc1" * 16
        path = _stored(tmp_path / "document.bin", three_fields)

        assert read_leading_fields(path, frozenset({LEADING, FOLLOWING})) == {LEADING: 1, FOLLOWING: 2}


class TestAStoredDocumentsFraming:
    def test_the_named_fields_read_through_the_framing(self, tmp_path: Path) -> None:
        document = {LEADING: {"version": "2.1"}, FOLLOWING: [1, 2], TRAILING: b"\x00" * 4096}
        payload = msgpack.packb(document, use_bin_type=True)
        path = _stored(tmp_path / "document.bin", compress_document(payload))

        fields = read_leading_fields(path, frozenset({LEADING, FOLLOWING}))

        assert fields == {LEADING: document[LEADING], FOLLOWING: document[FOLLOWING]}

    def test_a_document_whose_framing_is_cut_short_holds_no_fields(self, tmp_path: Path) -> None:
        stored = compress_document(msgpack.packb({LEADING: "x" * 4096}, use_bin_type=True))
        path = _stored(tmp_path / "document.bin", stored[:24])

        assert not read_leading_fields(path, frozenset({LEADING}))

    def test_a_document_whose_framing_is_damaged_holds_no_fields(self, tmp_path: Path) -> None:
        stored = compress_document(msgpack.packb({LEADING: "x" * 4096}, use_bin_type=True))
        path = _stored(tmp_path / "document.bin", stored[:20] + b"\xff" * 256)

        assert not read_leading_fields(path, frozenset({LEADING}))


class TestAFrontThatDecodesAsNoMap:
    def test_an_empty_file_holds_no_fields(self, tmp_path: Path) -> None:
        path = _stored(tmp_path / "document.bin", b"")

        assert not read_leading_fields(path, frozenset({LEADING}))

    def test_a_document_of_another_shape_holds_no_fields(self, tmp_path: Path) -> None:
        path = _stored(tmp_path / "document.bin", msgpack.packb([LEADING, 1], use_bin_type=True))

        assert not read_leading_fields(path, frozenset({LEADING}))

    def test_bytes_of_no_format_hold_no_fields(self, tmp_path: Path) -> None:
        path = _stored(tmp_path / "document.bin", b"\xc1\xc1\xc1\xc1")

        assert not read_leading_fields(path, frozenset({LEADING}))

    def test_a_document_cut_short_holds_no_fields(self, tmp_path: Path) -> None:
        whole = msgpack.packb({LEADING: "x" * 64}, use_bin_type=True)
        path = _stored(tmp_path / "document.bin", whole[:16])

        assert not read_leading_fields(path, frozenset({LEADING}))
