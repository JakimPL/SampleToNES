import tempfile
from pathlib import Path
from typing import Final

import pytest

from automation.environment import (
    HOMES_VARIABLE,
    SHARD_VARIABLE,
    ScenarioFolders,
    Shard,
    ShardError,
    child_environment,
    homes_root,
    shard,
)

NODEID: Final[str] = "tests/screens/test_case.py::TestCase::test_it"
DISPLAY: Final[str] = ":9"


class TestWhereTheHomesGo:
    def test_the_homes_go_to_the_system_s_temporary_folder(self) -> None:
        assert homes_root({}) == Path(tempfile.gettempdir())

    def test_the_variable_moves_them(self) -> None:
        assert homes_root({HOMES_VARIABLE: "/work/homes"}) == Path("/work/homes")


class TestTheScenarioProcessEnvironment:
    """The process keeps the machine's temporary folder, whose short path its socket files fit in."""

    def test_the_temporary_folder_is_the_machine_s(self, tmp_path: Path) -> None:
        folders = ScenarioFolders.of(NODEID, homes=tmp_path / "homes", kept=tmp_path / "kept")

        environment = child_environment({"TMPDIR": "/tmp"}, folders, display=DISPLAY)

        assert environment["TMPDIR"] == "/tmp"
        assert environment["HOME"] == str(folders.home)

    def test_a_process_told_no_temporary_folder_is_told_none(self, tmp_path: Path) -> None:
        folders = ScenarioFolders.of(NODEID, homes=tmp_path / "homes", kept=tmp_path / "kept")

        environment = child_environment({}, folders, display=DISPLAY)

        assert "TMPDIR" not in environment


class TestTheShard:
    """A run spread over machines takes every count-th scenario from its own index, and the parts cover the
    collection once.
    """

    def test_no_variable_means_the_whole_collection(self) -> None:
        assert shard({}) is None

    def test_the_variable_names_the_part(self) -> None:
        assert shard({SHARD_VARIABLE: "2/3"}) == Shard(index=2, count=3)

    def test_the_parts_cover_every_position_once(self) -> None:
        parts = [Shard.of(f"{index}/3") for index in (1, 2, 3)]

        keepers = [[part for part in parts if part.keeps(position)] for position in range(7)]

        assert [len(kept) for kept in keepers] == [1] * 7
        assert [kept[0].index for kept in keepers] == [1, 2, 3, 1, 2, 3, 1]

    def test_one_part_keeps_everything(self) -> None:
        assert all(Shard.of("1/1").keeps(position) for position in range(5))

    @pytest.mark.parametrize("stated", ["3", "a/b", "0/3", "4/3", "1/0", "-1/3", "1/3/1"])
    def test_other_readings_are_refused(self, stated: str) -> None:
        with pytest.raises(ShardError):
            Shard.of(stated)
