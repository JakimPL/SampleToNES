import tarfile
from pathlib import Path
from typing import Dict, Final, List, Tuple

from sampletones_core.configs import Config
from sampletones_tools.calibration.config.manifest import CorpusManifest, NesmdbPiece, Split

from .families import Family
from .item import CorpusItem
from .midi import read_midi
from .nes import written_item
from .nesmdb import nesmdb_frames

NESMDB_CATEGORY_PREFIX: Final[str] = "nesmdb"


class MissingPieceError(FileNotFoundError):
    """Raised when an archive holds no piece of the name a manifest gives."""


def nesmdb_category(split: Split) -> str:
    """The category an NES-MDB piece of ``split`` is reported under, so the two splits stand apart."""
    return f"{NESMDB_CATEGORY_PREFIX}-{split.value}"


def manifest_catalog(manifest: CorpusManifest) -> List[Tuple[Family, str]]:
    """Every category the manifest's sounds fall in, beside its family, in the order it holds them."""
    return list(dict.fromkeys((Family.SEQUENCES, nesmdb_category(item.split)) for item in manifest.items))


def build_manifest(config: Config, *, manifest: CorpusManifest) -> List[CorpusItem]:
    """The manifest's sounds: each NES-MDB window rendered through the channels from the frames it writes.

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
    pieces = _read_pieces(manifest.items)
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
        for item in manifest.items
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
