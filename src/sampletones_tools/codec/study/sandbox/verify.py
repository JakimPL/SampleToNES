from typing import Sequence

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_tools.codec.study.sandbox.decode import play_tokens
from sampletones_tools.codec.study.sandbox.parse import StudyParse


def verify_baseline(
    parses: Sequence[StudyParse],
    compressed: CompressedPlanes,
) -> None:
    """Holds the sandbox's baseline grammar to the streams the production codec wrote.

    The sandbox prices every grammar on its own parser, so the parser is proven on the one
    grammar whose answer is known: each plane under the baseline grammar costs exactly the
    bytes the production stream takes, or the study is reading the planes wrong.

    Args:
        parses: Every plane under the baseline grammar.
        compressed: The production encoding of the same planes over the same dictionary.

    Raises:
        ValueError: If a plane is priced differently from the stream the codec wrote.
    """
    for name, parse, stream in zip(PlaneOrder.names(), parses, compressed.streams):
        if parse.size != len(stream):
            raise ValueError(
                f"the sandbox reads {name} as {parse.size} bytes where the codec wrote {len(stream)}; "
                "the baseline grammar has parted from the production parser"
            )


def plays_back(
    parses: Sequence[StudyParse],
    table: PhraseTable,
    planes: SongPlanes,
) -> bool:
    """Whether every plane's tokens play back to the plane they were written from.

    Args:
        parses: Every plane's parse, in the order the song block writes them.
        table: The dictionary the tokens name.
        planes: The planes the parses were read from.

    Returns:
        bool: Whether the encoding is lossless.
    """
    return all(play_tokens(parse.tokens, table, planes.ticks) == plane for parse, plane in zip(parses, planes.planes))
