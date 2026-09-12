from typing import Final

from codec_study.corpus.song import StudySong
from codec_study.variants.variant import Variant, VariantKind
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.encode import encode_planes
from sampletones_player.compression.options import EVERY_LAYER

BASELINE_NAME: Final[str] = "baseline"
NO_LOOP_BOUNDARIES: Final[frozenset[int]] = frozenset()


def encode_baseline(song: StudySong) -> CompressedPlanes:
    """Encodes a song as the export does, every layer on and the search at its default budget.

    Args:
        song: The song to encode.

    Returns:
        CompressedPlanes: The dictionary and the token streams.
    """
    return encode_planes(
        song.planes,
        song.seeds,
        options=EVERY_LAYER,
        boundaries=NO_LOOP_BOUNDARIES,
    )


BASELINE: Final[Variant] = Variant(
    name=BASELINE_NAME,
    hypothesis="",
    kind=VariantKind.BASELINE,
    note="",
    encode=encode_baseline,
)
