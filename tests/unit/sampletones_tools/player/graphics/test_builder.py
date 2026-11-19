from pathlib import Path
from typing import Final

from sampletones_player.specification.shell import PATTERNS_NAME
from sampletones_tools.player.assembler.layout import (
    ASSEMBLY_DIRECTORY,
    DECK_INCLUDE_NAME,
    DECK_SOURCE_NAME,
    INCLUDE_DIRECTORY,
    SOURCE_DIRECTORY,
)
from sampletones_tools.player.graphics.builder import TEXT_ENCODING, build_patterns, build_shell_data
from sampletones_tools.player.graphics.paths import PATTERNS_DIRECTORY
from tests.suite.base import BaseTestSuite

STALE_MESSAGE: Final[str] = "run `uv run sampletones tiles`, then `uv run sampletones driver`"


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
        assert (PATTERNS_DIRECTORY / PATTERNS_NAME).read_bytes() == shipped_patterns, STALE_MESSAGE


class TestTheBuiltShellData(BaseTestSuite):
    def test_the_equates_and_the_tables_land_where_asked(self, tmp_path: Path) -> None:
        build_shell_data(tmp_path / "include", tmp_path / "source")

        assert (tmp_path / "include" / DECK_INCLUDE_NAME).is_file()
        assert (tmp_path / "source" / DECK_SOURCE_NAME).is_file()

    def test_the_shipped_equates_are_the_ones_the_screen_states(self, tmp_path: Path) -> None:
        build_shell_data(tmp_path, tmp_path)

        shipped = (ASSEMBLY_DIRECTORY / INCLUDE_DIRECTORY / DECK_INCLUDE_NAME).read_text(encoding=TEXT_ENCODING)
        assert (tmp_path / DECK_INCLUDE_NAME).read_text(encoding=TEXT_ENCODING) == shipped, STALE_MESSAGE

    def test_the_shipped_tables_are_the_ones_the_screen_states(self, tmp_path: Path) -> None:
        build_shell_data(tmp_path, tmp_path)

        shipped = (ASSEMBLY_DIRECTORY / SOURCE_DIRECTORY / DECK_SOURCE_NAME).read_text(encoding=TEXT_ENCODING)
        assert (tmp_path / DECK_SOURCE_NAME).read_text(encoding=TEXT_ENCODING) == shipped, STALE_MESSAGE
