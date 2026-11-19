import os
import sys
import time
from argparse import ArgumentParser
from typing import Dict, Final, Sequence

import pytest

from assets.pictures.paths import IMAGES_DIRECTORY, KEPT_DIRECTORY, PICTURE_SUFFIX, SCENES_DIRECTORY
from assets.pictures.writer import written_since
from assets.stage.paths import HOMES_DIRECTORY
from assets.stage.runner import NOTHING_TO_RUN, ensure_demo_tree, pytest_arguments, run_environment
from sampletones_shared.paths.source import REPOSITORY_ROOT

PROGRAM: Final[str] = "python -m assets.pictures"
DESCRIPTION: Final[str] = "draw the guide's and the README's pictures of the application from the demo tree"
SCREEN: Final[str] = "1700x1300"
WORKERS: Final[str] = "4"
NAMING: Final[Dict[str, str]] = {
    "python_files": "*_scenes.py",
    "python_classes": "*Scenes",
    "python_functions": "picture_*",
}
ALONE_MARKER: Final[str] = "alone"
MARKERS: Final[Dict[str, str]] = {ALONE_MARKER: "a scene drawn with no other scene's home beside its own"}


def main(argv: Sequence[str]) -> int:
    """Makes the demo tree where it is missing, draws every scene, and reports each picture written.

    The scenes run on a few workers, and the scenes marked as drawn alone run one at a time after
    them, once every other worker has let its homes go: a picture of the file browser shows the
    folders beside the scene's home, and a home beside it is named after the run that made it.
    """
    ArgumentParser(prog=PROGRAM, description=DESCRIPTION).parse_args(list(argv))
    ensure_demo_tree()
    HOMES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        run_environment(
            dict(os.environ),
            screen=SCREEN,
            kept=KEPT_DIRECTORY,
            homes=HOMES_DIRECTORY,
            repository=REPOSITORY_ROOT,
        )
    )
    started = time.time()
    status = int(
        pytest.main(
            pytest_arguments(
                SCENES_DIRECTORY,
                NAMING,
                markers=MARKERS,
                workers=WORKERS,
                selection=f"not {ALONE_MARKER}",
            )
        )
    )
    if status == 0:
        alone = int(
            pytest.main(
                pytest_arguments(
                    SCENES_DIRECTORY,
                    NAMING,
                    markers=MARKERS,
                    workers=None,
                    selection=ALONE_MARKER,
                )
            )
        )
        status = 0 if alone == NOTHING_TO_RUN else alone

    for path in written_since(IMAGES_DIRECTORY, started, PICTURE_SUFFIX):
        print(f"Wrote {path}")

    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
