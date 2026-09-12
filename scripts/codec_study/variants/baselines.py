from time import process_time
from typing import Dict

from codec_study.corpus.song import StudySong
from codec_study.measure import Encoding, production_encoding
from codec_study.sandbox.reference import Reference, reference
from codec_study.variants.production import BASELINE_NAME, compress_baseline
from codec_study.variants.variant import Variant, VariantKind
from sampletones_player.compression.compressed import CompressedPlanes


class Baselines:
    """The production encoding of each song, taken once and read by every variant built on it.

    A run measures a song under every variant before moving to the next, so one song's
    encoding is kept at a time: the baseline variant writes it, and the sandbox reads the
    dictionary and the planes' matches from there in place of encoding the song again. A
    song asked for before its baseline ran is encoded on the spot.
    """

    def __init__(self) -> None:
        self._compressed: Dict[str, CompressedPlanes] = {}
        self._references: Dict[str, Reference] = {}

    def encode(self, song: StudySong) -> Encoding:
        """Encodes a song as the export does today, keeping the result for the sandbox.

        Args:
            song: The song to encode.

        Returns:
            Encoding: The encoding, its streams kept as written.
        """
        started = process_time()
        compressed = compress_baseline(song)
        seconds = process_time() - started
        self._compressed = {song.name: compressed}
        self._references = {}
        return production_encoding(song, compressed, seconds)

    def compressed(self, song: StudySong) -> CompressedPlanes:
        """The production encoding of ``song``.

        Args:
            song: The song.

        Returns:
            CompressedPlanes: The dictionary and the streams the codec wrote.
        """
        remembered = self._compressed.get(song.name)
        if remembered is None:
            remembered = compress_baseline(song)
            self._compressed = {song.name: remembered}
            self._references = {}

        return remembered

    def reference(self, song: StudySong) -> Reference:
        """What every grammar prices ``song`` against.

        Args:
            song: The song.

        Returns:
            Reference: The song, its dictionary, its matches and its baseline parse.
        """
        remembered = self._references.get(song.name)
        if remembered is None:
            remembered = reference(song, self.compressed(song))
            self._references = {song.name: remembered}

        return remembered


def baseline_variant(baselines: Baselines) -> Variant:
    """The codec as it stands, which every other variant is held against.

    Args:
        baselines: Where the encodings are kept for the variants built on them.

    Returns:
        Variant: The baseline.
    """
    return Variant(
        name=BASELINE_NAME,
        hypothesis="",
        kind=VariantKind.BASELINE,
        note="",
        encode=baselines.encode,
        needs_seeds=False,
    )
