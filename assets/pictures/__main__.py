import os
import sys
import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, Final, List, Optional, Sequence

import pytest

from assets.demo.tree import build_demo
from assets.pictures.paths import (
    DEMO_DIRECTORY,
    HOMES_DIRECTORY,
    IMAGES_DIRECTORY,
    KEPT_DIRECTORY,
    PICTURE_SUFFIX,
    SCENES_DIRECTORY,
)
from assets.pictures.writer import written_since
from automation.environment import KEPT_VARIABLE, SCREEN_VARIABLE
from sampletones_shared.paths.source import REPOSITORY_ROOT

PROGRAM: Final[str] = "python -m assets.pictures"
DESCRIPTION: Final[str] = "draw the guide's and the README's pictures of the application from the demo tree"
SCREEN: Final[str] = "1700x1300"
WORKERS: Final[str] = "4"
TEMPORARY_VARIABLE: Final[str] = "TMPDIR"
HIDDEN_PREFIX: Final[str] = "."
NAMING: Final[Dict[str, str]] = {
    "python_files": "*_scenes.py",
    "python_classes": "*Scenes",
    "python_functions": "picture_*",
}
ALONE_MARKER: Final[str] = "alone"
ALONE_MARKER_WORDS: Final[str] = "a scene drawn with no other scene's home beside its own"
NOTHING_TO_RUN: Final[int] = int(pytest.ExitCode.NO_TESTS_COLLECTED)


def pytest_arguments(
    scenes: Path,
    naming: Dict[str, str],
    *,
    workers: Optional[str],
    selection: str,
) -> List[str]:
    """The arguments the scenes run under: their folder, their naming, the marker expression ``selection``
    picks them by, and ``workers`` workers, or one process at a time for ``None``, without coverage.
    """
    overrides = [argument for key, value in naming.items() for argument in ("-o", f"{key}={value}")]
    spread = ["-n", workers] if workers is not None else []
    return [
        str(scenes),
        *overrides,
        "-o",
        f"markers={ALONE_MARKER}: {ALONE_MARKER_WORDS}",
        "-m",
        selection,
        *spread,
        "--no-cov",
        "-p",
        "no:cacheprovider",
        "-q",
    ]


def run_environment(base: Dict[str, str], *, kept: Path, homes: Path, repository: Path) -> Dict[str, str]:
    """The environment the scenes run under: a screen large enough for every picture, and records kept apart.

    The scenario homes go under the repository when its path holds no hidden folder, so the paths the
    pictures show read as a home under ``/home``; a checkout under a hidden folder keeps the system's
    temporary folder, which the application's browsers can reach.
    """
    environment = dict(base)
    environment[SCREEN_VARIABLE] = SCREEN
    environment[KEPT_VARIABLE] = str(kept)
    if not any(part.startswith(HIDDEN_PREFIX) for part in repository.parts):
        environment[TEMPORARY_VARIABLE] = str(homes)

    return environment


def main(argv: Sequence[str]) -> int:
    """Makes the demo tree where it is missing, draws every scene, and reports each picture written.

    The scenes run on a few workers, and the scenes marked as drawn alone run one at a time after
    them, once every other worker has let its homes go: a picture of the file browser shows the
    folders beside the scene's home, and a home beside it is named after the run that made it.
    """
    ArgumentParser(prog=PROGRAM, description=DESCRIPTION).parse_args(list(argv))
    if not DEMO_DIRECTORY.is_dir():
        build_demo(DEMO_DIRECTORY)

    HOMES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        run_environment(
            dict(os.environ),
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
