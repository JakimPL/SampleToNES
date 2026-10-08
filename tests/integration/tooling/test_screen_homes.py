import os
import tempfile
from pathlib import Path
from typing import Final

import pytest

from automation import homes
from automation.paths import HOMES_PREFIX, PROCESSES_DIRECTORY

GONE_PROCESS: Final[int] = 2**22 + 1
MISSING_FOLDER: Final[str] = "no-processes"
TAIL: Final[str] = "tail"

requires_the_process_folder = pytest.mark.skipif(
    not PROCESSES_DIRECTORY.is_dir(),
    reason="the sweep reads which processes run from the process folder Linux keeps",
)


@pytest.fixture(name="temporary")
def temporary_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The temporary folder the worker's homes are made in, standing apart from the machine's own."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path


def left_homes(parent: Path, process: int) -> Path:
    """A homes folder a worker of ``process`` made and left behind."""
    folder = parent / f"{HOMES_PREFIX}{process}{homes.PROCESS_SEPARATOR}{TAIL}"
    folder.mkdir()
    return folder


class TestTheStaleHomesSweep:
    """A worker's first scenario lets go of the homes a gone worker left, and keeps a running worker's.

    The process id beyond the largest one Linux hands out names a worker that has gone.
    """

    @requires_the_process_folder
    def test_the_homes_of_a_gone_worker_go(self, temporary: Path) -> None:
        stale = left_homes(temporary, GONE_PROCESS)

        homes.make_worker_homes()

        assert not stale.exists()

    @requires_the_process_folder
    def test_the_homes_of_a_running_worker_stay(self, temporary: Path) -> None:
        running = left_homes(temporary, os.getppid())

        made = homes.make_worker_homes()

        assert running.exists()
        assert made.exists()

    def test_every_homes_folder_stays_where_the_process_folder_is_missing(
        self,
        temporary: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A machine with no process folder tells no worker gone, so the sweep leaves every folder as it is."""
        monkeypatch.setattr(homes, "PROCESSES_DIRECTORY", temporary / MISSING_FOLDER)
        left = [left_homes(temporary, GONE_PROCESS), left_homes(temporary, os.getppid())]

        homes.make_worker_homes()

        assert all(folder.exists() for folder in left)
