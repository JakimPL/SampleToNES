from dataclasses import dataclass
from pathlib import Path

from assets.demo.paths import piece_document_path
from assets.demo.specification import DemoSpecification
from assets.footage.specification import Footage
from assets.stage.paths import DEMO_DIRECTORY
from assets.stage.runner import ensure_demo_tree


@dataclass(frozen=True)
class LocatedDocument:
    """Where the footage's reconstruction is read from, and the folder its recordings' relative paths start at.

    The demo tree's piece names its recordings relative to the tree, so it is read from inside the tree; a
    document of a specification of its own names them as it was converted.
    """

    path: Path
    working_directory: Path


def located_document(footage: Footage, specification: Path) -> LocatedDocument:
    """The reconstruction ``footage`` films, the demo tree's piece where it names none, the tree made where it is
    missing.
    """
    if footage.document is None:
        ensure_demo_tree()
        piece = DemoSpecification.load().recordings.piece.name
        return LocatedDocument(path=piece_document_path(DEMO_DIRECTORY, piece), working_directory=DEMO_DIRECTORY)

    folder = specification.parent
    return LocatedDocument(path=(folder / footage.document).resolve(), working_directory=folder)
