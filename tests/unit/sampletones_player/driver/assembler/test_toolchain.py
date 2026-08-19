import shutil
import sys
from pathlib import Path
from typing import Final

import pytest

from sampletones_player.driver.assembler.toolchain import (
    ASSEMBLER,
    INSTALL_HINTS,
    LINKER,
    Toolchain,
)
from sampletones_shared.exceptions import DriverBuildError, ToolchainMissingError
from sampletones_shared.utils.system.system import System
from tests.suite.base import BaseTestSuite

FAILING_PROGRAM: Final[str] = "import sys; sys.stderr.write('boom'); sys.exit(1)"


class TestTheToolchainALocatedBuildRuns(BaseTestSuite):
    """The cc65 programs a build resolves before it produces anything."""

    def test_every_system_states_how_it_installs_cc65(self) -> None:
        assert set(INSTALL_HINTS) == set(System)

    def test_a_located_program_answers_with_its_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        installed = Path("/usr/local/bin") / ASSEMBLER
        monkeypatch.setattr(shutil, "which", lambda program: str(installed))
        assert Toolchain.locate() == Toolchain(assembler=installed, linker=installed)

    def test_a_missing_program_names_itself(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(shutil, "which", lambda program: None)
        with pytest.raises(ToolchainMissingError, match=ASSEMBLER):
            Toolchain.locate()

    def test_a_missing_program_states_how_this_system_installs_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(shutil, "which", lambda program: None)
        with pytest.raises(ToolchainMissingError, match=INSTALL_HINTS[System.current()]):
            Toolchain.find(LINKER)

    def test_a_program_that_fails_carries_what_it_printed(self) -> None:
        with pytest.raises(DriverBuildError, match="boom"):
            Toolchain.run([sys.executable, "-c", FAILING_PROGRAM])
