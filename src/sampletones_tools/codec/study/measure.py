from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.decode import decode_planes
from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_tools.codec.study.corpus.song import StudySong


@dataclass(frozen=True)
class Encoding:
    """What a variant wrote a song as, priced in the bytes the song block counts.

    A variant of the encoder writes the grammar the driver reads today, and its streams are
    kept as the bytes they are. A variant of the grammar is priced at token level, its streams
    stated as the bytes each would take, so the two kinds sit in one report on the same terms.

    Attributes:
        header: The bytes the song block's header takes, which a format stating more of itself grows.
        phrases: The phrases the dictionary holds.
        dictionary: The bytes the dictionary takes.
        streams: The bytes each plane's stream takes, in the order the song block writes them.
        seconds: The processor time the encoding took.
        lossless: Whether the streams play back to the planes they were written from.
        written: The streams as the driver reads them, where the variant writes its grammar.
    """

    header: int
    phrases: int
    dictionary: int
    streams: Tuple[int, ...]
    seconds: float
    lossless: bool
    written: Optional[CompressedPlanes]


Encoder = Callable[[StudySong], Encoding]


@dataclass(frozen=True)
class Measurement:
    """One song encoded under one variant.

    Attributes:
        song: The song encoded.
        variant: The name of the variant the encoding was built by.
        encoding: What the variant wrote, and what writing it cost.
    """

    song: StudySong
    variant: str
    encoding: Encoding

    @property
    def block(self) -> int:
        """The bytes the whole song block takes: header, pitch table, dictionary and streams."""
        return self.encoding.header + len(self.song.pitches.data) + self.dictionary + self.streams

    @property
    def dictionary(self) -> int:
        """The bytes the dictionary takes."""
        return self.encoding.dictionary

    @property
    def streams(self) -> int:
        """The bytes the token streams take together."""
        return sum(self.encoding.streams)

    @property
    def phrases(self) -> int:
        """The phrases the dictionary holds."""
        return self.encoding.phrases

    @property
    def seconds(self) -> float:
        """The processor time the encoding took."""
        return self.encoding.seconds

    @property
    def lossless(self) -> bool:
        """Whether the streams play back to the planes they were written from."""
        return self.encoding.lossless

    @property
    def bytes_per_tick(self) -> float:
        """The bytes each tick of the song costs, the whole block counted."""
        return self.block / self.song.ticks


def production_encoding(
    song: StudySong,
    compressed: CompressedPlanes,
    seconds: float,
) -> Encoding:
    """What the production codec wrote a song as, played back through the production decoder.

    Args:
        song: The song encoded.
        compressed: The dictionary and the streams the codec wrote.
        seconds: The processor time the encoding took.

    Returns:
        Encoding: The encoding, its streams kept as written.
    """
    return Encoding(
        header=SONG_HEADER_SIZE,
        phrases=len(compressed.phrases),
        dictionary=compressed.phrases.size,
        streams=tuple(len(stream) for stream in compressed.streams),
        seconds=seconds,
        lossless=decode_planes(compressed) == song.planes,
        written=compressed,
    )


def measure(
    song: StudySong,
    variant: str,
    encode: Encoder,
) -> Measurement:
    """Encodes a song under a variant.

    Args:
        song: The song to encode.
        variant: The name of the variant.
        encode: What the variant writes the song as.

    Returns:
        Measurement: The encoding under the song and variant it belongs to.
    """
    return Measurement(
        song=song,
        variant=variant,
        encoding=encode(song),
    )
