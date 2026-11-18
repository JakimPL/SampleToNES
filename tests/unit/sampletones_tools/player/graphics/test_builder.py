from pathlib import Path

from sampletones_player.specification.shell import PATTERNS_NAME
from sampletones_tools.player.graphics.builder import build_patterns
from sampletones_tools.player.graphics.paths import PATTERNS_DIRECTORY
from tests.suite.base import BaseTestSuite


class TestTheBuiltPatternTables(BaseTestSuite):
    def test_the_written_file_holds_the_tables_the_sheet_draws(self, tmp_path: Path, shipped_patterns: bytes) -> None:
        returned = build_patterns(tmp_path)

        assert returned == shipped_patterns
        assert (tmp_path / PATTERNS_NAME).read_bytes() == shipped_patterns

    def test_a_missing_destination_is_created(self, tmp_path: Path, shipped_patterns: bytes) -> None:
        destination = tmp_path / "nested" / "binary"

        build_patterns(destination)

        assert (destination / PATTERNS_NAME).read_bytes() == shipped_patterns

    def test_the_shipped_tables_are_the_ones_the_sheet_draws(self, shipped_patterns: bytes) -> None:
        """A sheet edited without running ``sampletones tiles`` leaves the shipped tables stale."""
        assert (PATTERNS_DIRECTORY / PATTERNS_NAME).read_bytes() == shipped_patterns
