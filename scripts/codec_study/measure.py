from dataclasses import dataclass
from time import process_time
from typing import Callable

from codec_study.corpus.song import StudySong
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.decode import decode_planes
from sampletones_player.specification.song import SONG_HEADER_SIZE

Encoder = Callable[[StudySong], CompressedPlanes]


@dataclass(frozen=True)
class Measurement:
    """One song encoded under one variant, with what the encoding cost and whether it plays back.

    Attributes:
        song: The song encoded.
        variant: The name of the variant the encoding was built by.
        compressed: The dictionary and the token streams the variant wrote.
        seconds: The processor time the encoding took.
        lossless: Whether the streams play back to the planes they were written from.
    """

    song: StudySong
    variant: str
    compressed: CompressedPlanes
    seconds: float
    lossless: bool

    @property
    def block(self) -> int:
        """The bytes the whole song block takes: header, pitch table, dictionary and streams."""
        return SONG_HEADER_SIZE + len(self.song.pitches.data) + self.compressed.size

    @property
    def dictionary(self) -> int:
        """The bytes the dictionary takes."""
        return self.compressed.phrases.size

    @property
    def streams(self) -> int:
        """The bytes the token streams take together."""
        return sum(len(stream) for stream in self.compressed.streams)

    @property
    def bytes_per_tick(self) -> float:
        """The bytes each tick of the song costs, the whole block counted."""
        return self.block / self.song.ticks


def measure(
    song: StudySong,
    variant: str,
    encode: Encoder,
) -> Measurement:
    """Encodes a song under a variant, timing the encoding and playing it back.

    Args:
        song: The song to encode.
        variant: The name of the variant.
        encode: What the variant writes the song as.

    Returns:
        Measurement: The encoding, its cost and whether it plays back.
    """
    started = process_time()
    compressed = encode(song)
    seconds = process_time() - started
    return Measurement(
        song=song,
        variant=variant,
        compressed=compressed,
        seconds=seconds,
        lossless=decode_planes(compressed) == song.planes,
    )
