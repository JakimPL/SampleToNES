import tarfile
from pathlib import Path
from typing import Dict, Final, List, Tuple

import numpy as np

from sampletones_core.audio.io import read_stems
from sampletones_core.configs import Config
from sampletones_core.headless.conversion.request import load_stems
from sampletones_tools.calibration.config.manifest import CorpusManifest, NesmdbPiece, Split

from .families import Family
from .item import CorpusItem, StemsSources
from .midi import read_midi
from .nes import written_item
from .nesmdb import nesmdb_frames

NESMDB_CATEGORY_PREFIX: Final[str] = "nesmdb"


class MissingPieceError(FileNotFoundError):
    """Raised when an archive holds no piece of the name a manifest gives."""


def nesmdb_category(split: Split) -> str:
    """The category an NES-MDB piece of ``split`` is reported under, so the two splits stand apart."""
    return f"{NESMDB_CATEGORY_PREFIX}-{split.value}"


def pieces_catalog(manifest: CorpusManifest) -> List[Tuple[Family, str]]:
    """Every category the manifest's NES-MDB pieces fall in, beside its family, in the order it holds them."""
    return list(dict.fromkeys((Family.SEQUENCES, nesmdb_category(item.split)) for item in manifest.pieces))


def recordings_catalog(manifest: CorpusManifest) -> List[Tuple[Family, str]]:
    """Every category the manifest's recordings fall in, beside its family, in the order it holds them."""
    return list(dict.fromkeys((Family(item.family), item.category) for item in manifest.recordings))


def build_recordings(config: Config, *, manifest: CorpusManifest) -> List[CorpusItem]:
    """The manifest's recordings, each read at the run's rate and at the level it was captured.

    Recordings under a stems setup are held as stems, converted under that setup; a single
    recording is converted over the run's channels.

    Args:
        config: The configuration the run converts with.
        manifest: The local sounds.

    Returns:
        List[CorpusItem]: One item per recording entry, in the order the manifest lists them.

    Raises:
        ValueError: If a stems setup names a different number of entries than its recordings, or
            holds no stems setup.
        FileNotFoundError: If a recording is missing.
    """
    items: List[CorpusItem] = []
    for item in manifest.recordings:
        recordings = tuple(
            np.asarray(audio, dtype=np.float32)
            for audio in read_stems(item.sources, target_sample_rate=config.library.sample_rate)
        )
        stems = None if item.stems is None else load_stems(item.stems)
        if stems is not None and len(stems.entries) != len(recordings):
            raise ValueError(f"{item.name!r} names {len(recordings)} recordings for {len(stems.entries)} stems")

        items.append(
            CorpusItem(
                name=item.name,
                family=Family(item.family),
                category=item.category,
                listed=item.listed,
                audio=np.sum(recordings, axis=0).astype(np.float32),
                truth=None,
                channels=None if stems is None else frozenset(stems.covered_channels),
                stems=None if stems is None else StemsSources(sources=recordings, config=stems),
            )
        )

    return items


def build_pieces(config: Config, *, manifest: CorpusManifest) -> List[CorpusItem]:
    """The manifest's NES-MDB pieces: each window rendered through the channels from the frames it writes.

    A review piece is listed, so the page plays it. A held-out piece keeps its record alone, which
    keeps it out of listening while the review pieces are tuned on.

    Args:
        config: The configuration the frames are rendered at, the one the run converts with.
        manifest: The local sounds.

    Returns:
        List[CorpusItem]: One item per piece, in the order the manifest lists them.

    Raises:
        MissingPieceError: If an archive holds no piece of a name the manifest gives.
        MidiFormatError: If a piece holds no MIDI file this reader takes.
    """
    pieces = _read_pieces(manifest.pieces)
    return [
        written_item(
            item.name,
            Family.SEQUENCES,
            nesmdb_category(item.split),
            listed=item.split is Split.REVIEW,
            instructions=nesmdb_frames(
                read_midi(pieces[(item.archive, item.member)]),
                start_frame=item.start_frame,
                frames=item.frames,
                rate=config.library.nes_frequency,
            ),
            config=config,
        )
        for item in manifest.pieces
    ]


def _read_pieces(items: List[NesmdbPiece]) -> Dict[Tuple[Path, str], bytes]:
    """The bytes of every piece the items name, each archive opened once and read member by member."""
    wanted: Dict[Path, List[str]] = {}
    for item in items:
        wanted.setdefault(item.archive, []).append(item.member)

    pieces: Dict[Tuple[Path, str], bytes] = {}
    for archive, members in wanted.items():
        with tarfile.open(archive, "r:*") as tar:
            names = set(tar.getnames())
            for member in members:
                handle = tar.extractfile(member) if member in names else None
                if handle is None:
                    raise MissingPieceError(f"'{archive}' holds no piece '{member}'")
                pieces[(archive, member)] = handle.read()

    return pieces
