from datetime import UTC, datetime
from pathlib import Path

import pytest

from sampletones_tools.runs import (
    BOARD_STAMP,
    RUN_STAMP,
    stamped_board_directory,
    stamped_directory,
    stamped_run_directory,
)


class TestStampedRunDirectory:
    def test_a_run_lands_under_the_root_named_by_its_start(self, tmp_path: Path) -> None:
        before = datetime.now(UTC).replace(microsecond=0)

        directory = stamped_run_directory(tmp_path)

        started = datetime.strptime(directory.name, RUN_STAMP).replace(tzinfo=UTC)
        assert directory.parent == tmp_path
        assert before <= started <= datetime.now(UTC)


class TestStampedBoardDirectory:
    def test_a_page_lands_under_the_root_named_by_the_moment_it_is_built(self, tmp_path: Path) -> None:
        directory = stamped_board_directory(tmp_path)

        assert directory.parent == tmp_path
        assert datetime.strptime(directory.name, BOARD_STAMP)


class TestStampedDirectory:
    @pytest.mark.parametrize("stamp", (RUN_STAMP, BOARD_STAMP))
    def test_a_directory_is_named_by_the_stamp_it_is_given(self, tmp_path: Path, stamp: str) -> None:
        directory = stamped_directory(tmp_path, stamp)

        assert datetime.strptime(directory.name, stamp)

    def test_the_two_stamps_tell_a_run_from_a_page(self) -> None:
        assert RUN_STAMP != BOARD_STAMP
