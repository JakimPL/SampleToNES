from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_shared.paths.user import LIBRARY_DIRECTORY, RECONSTRUCTIONS_DIRECTORY

WORKERS: Final[int] = 3


class TestASettingsCopyWithItsFoldersMoved:
    """A tree a test or a maker builds holds its library and reconstructions apart from the user's,
    and every other setting stays the shipped one."""

    def test_the_folders_stand_under_the_root(self, tmp_path: Path) -> None:
        config = Config.rooted_at(tmp_path)

        assert Path(config.general.library_directory) == tmp_path / LIBRARY_DIRECTORY.name
        assert Path(config.general.reconstructions_directory) == tmp_path / RECONSTRUCTIONS_DIRECTORY.name

    def test_every_other_setting_is_the_default(self, tmp_path: Path) -> None:
        config = Config.rooted_at(tmp_path)
        default = Config()

        moved = {"library_directory", "reconstructions_directory"}
        assert config.general.model_dump(exclude=moved) == default.general.model_dump(exclude=moved)
        assert (config.library, config.generation) == (default.library, default.generation)

    def test_moving_the_folders_leaves_the_original_as_it_was(self, tmp_path: Path) -> None:
        original = Config()

        original.with_directories(library=tmp_path / "a", reconstructions=tmp_path / "b")

        assert original == Config()

    def test_a_rooted_copy_survives_a_save_and_a_load(self, tmp_path: Path) -> None:
        config = Config.rooted_at(tmp_path)
        path = tmp_path / "config.json"
        config.save(path)

        assert Config.load(path) == config


class TestASettingsCopyWithItsWorkersSet:
    def test_the_workers_are_set_and_nothing_else_moves(self) -> None:
        config = Config().with_workers(WORKERS)

        assert config.general.max_workers == WORKERS
        assert config.general.model_dump(exclude={"max_workers"}) == Config().general.model_dump(
            exclude={"max_workers"}
        )

    @pytest.mark.parametrize("count", [0, -1])
    def test_fewer_than_one_worker_is_refused(self, count: int) -> None:
        with pytest.raises(ValidationError):
            Config().with_workers(count)
