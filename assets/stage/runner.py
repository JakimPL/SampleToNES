from pathlib import Path
from typing import Dict, Final, List, Optional

import pytest

from assets.demo.tree import build_demo
from assets.stage.paths import DEMO_DIRECTORY
from automation.environment import HOMES_VARIABLE, KEPT_VARIABLE, SCREEN_VARIABLE
from automation.homes import HIDDEN_PREFIX

NOTHING_TO_RUN: Final[int] = int(pytest.ExitCode.NO_TESTS_COLLECTED)
OWN_DEADLINE: Final[str] = "--timeout=0"


def pytest_arguments(
    scenes: Path,
    naming: Dict[str, str],
    *,
    markers: Dict[str, str],
    workers: Optional[str],
    selection: Optional[str],
) -> List[str]:
    """The arguments a maker's scenes run under: their folder, their naming, the markers they carry, the marker
    expression ``selection`` picks them by, or every scene for ``None``, and ``workers`` workers, or one process
    at a time for ``None``, without coverage.

    Each scene's process keeps the deadline the screen plugin gives it, so the run itself sets none.
    """
    overrides = [argument for key, value in naming.items() for argument in ("-o", f"{key}={value}")]
    declared = [argument for marker, words in markers.items() for argument in ("-o", f"markers={marker}: {words}")]
    picked = ["-m", selection] if selection is not None else []
    spread = ["-n", workers] if workers is not None else []
    return [
        str(scenes),
        *overrides,
        *declared,
        *picked,
        *spread,
        OWN_DEADLINE,
        "--no-cov",
        "-p",
        "no:cacheprovider",
        "-q",
    ]


def run_environment(
    base: Dict[str, str],
    *,
    screen: str,
    kept: Path,
    homes: Path,
    repository: Path,
) -> Dict[str, str]:
    """The environment a maker's scenes run under: a screen of ``screen`` pixels, and records kept apart.

    The scenario homes go under the repository when its path holds no hidden folder, so the paths the
    scenes show read as a home under ``/home``; a checkout under a hidden folder leaves the homes in the
    system's temporary folder, which the application's browsers can reach.
    """
    environment = dict(base)
    environment[SCREEN_VARIABLE] = screen
    environment[KEPT_VARIABLE] = str(kept)
    if not any(part.startswith(HIDDEN_PREFIX) for part in repository.parts):
        environment[HOMES_VARIABLE] = str(homes)

    return environment


def ensure_demo_tree() -> None:
    """Makes the demo tree the scenes are filmed on, where it is missing."""
    if not DEMO_DIRECTORY.is_dir():
        build_demo(DEMO_DIRECTORY)
