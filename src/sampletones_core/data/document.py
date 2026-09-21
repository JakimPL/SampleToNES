import gzip
from contextlib import contextmanager
from typing import Final, Iterator, Protocol

from sampletones_shared.types.path import Pathlike

DOCUMENT_MAGIC: Final[bytes] = b"\x1f\x8b"
COMPRESSION_LEVEL: Final[int] = 9
STATED_TIMESTAMP: Final[int] = 0


class ByteStream(Protocol):
    """A source bytes are read from a piece at a time, which is all a streaming read asks of one."""

    def read(self, size: int = ...) -> bytes:
        """The next ``size`` bytes, or the rest of the stream where the read names no size."""


def compress_document(payload: bytes) -> bytes:
    """The bytes a stored document is written as, its payload deflated.

    A document states its fields as names spelled out once per record, which is most of what a
    file of thousands of records holds, so the payload deflates to a fraction of its size. The
    bytes carry the deflate format's own magic, which tells a stored document apart from the
    payload of one written before this framing.

    The timestamp the framing carries is stated rather than taken from the clock, so saving one
    document twice writes the same bytes both times.

    Args:
        payload: The document's serialized payload.

    Returns:
        bytes: The bytes to store.
    """
    return gzip.compress(payload, compresslevel=COMPRESSION_LEVEL, mtime=STATED_TIMESTAMP)


def decompress_document(stored: bytes) -> bytes:
    """The payload a stored document holds.

    A document written before this framing carries its payload as it stands, and reads that way.

    Args:
        stored: The bytes read from the document.

    Returns:
        bytes: The document's serialized payload.
    """
    if stored.startswith(DOCUMENT_MAGIC):
        return gzip.decompress(stored)

    return stored


@contextmanager
def open_document(path: Pathlike) -> Iterator[ByteStream]:
    """Opens the document at ``path`` as a stream over the payload it holds.

    A read that ends at the front of a document reads the front of the file, which is what lets a
    library state its header ahead of its entries and be read by that header alone.

    Args:
        path: The stored document.

    Yields:
        ByteStream: The payload, from its first byte.
    """
    with open(path, "rb") as file:
        if file.read(len(DOCUMENT_MAGIC)) == DOCUMENT_MAGIC:
            file.seek(0)
            with gzip.GzipFile(fileobj=file, mode="rb") as stream:
                yield stream

            return

        file.seek(0)
        yield file
