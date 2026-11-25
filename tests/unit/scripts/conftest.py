from pathlib import Path

import pytest

from tests.suite.git import FIRST_FILE, ScratchRepository


@pytest.fixture
def repository(tmp_path: Path) -> ScratchRepository:
    """A repository holding one commit, its work tree exactly that commit's files."""
    root = tmp_path / "repository"
    root.mkdir()
    scratch = ScratchRepository(root)
    scratch.git("init", "--quiet")
    scratch.write(FIRST_FILE, "VALUE = 1\n")
    scratch.commit("Added: a module")
    return scratch
