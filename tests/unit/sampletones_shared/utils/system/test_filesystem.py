from pathlib import Path
from typing import Tuple

import pytest

from sampletones_shared.utils.system.filesystem import removal_takes, remove_path
from tests.suite.files import requires_symlinks


class TestRemovePath:
    def test_removes_file(self, tmp_path: Path) -> None:
        target = tmp_path / "library.stnlib"
        target.write_text("data")

        removed = remove_path(target)

        assert removed == target
        assert not target.exists()

    def test_removes_directory_recursively(self, tmp_path: Path) -> None:
        target = tmp_path / "reconstructions"
        nested = target / "set"
        nested.mkdir(parents=True)
        (nested / "tone.strec").write_text("data")

        removed = remove_path(target)

        assert removed == target
        assert not target.exists()

    @requires_symlinks
    def test_removes_directory_symlink_without_touching_target(
        self,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "tone.strec").write_text("data")
        link = tmp_path / "shortcut"
        link.symlink_to(target, target_is_directory=True)

        removed = remove_path(link)

        assert removed == link
        assert not link.exists()
        assert target.exists()

    def test_raises_for_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            remove_path(tmp_path / "missing")


def _tree(root: Path) -> None:
    """A folder of songs, a folder named like it beside it and one elsewhere, linked to in three ways."""
    (root / "songs" / "takes").mkdir(parents=True)
    (root / "elsewhere").mkdir()
    (root / "songs_beside").mkdir()
    for path in (
        root / "songs" / "a.stn",
        root / "songs" / "takes" / "b.stn",
        root / "elsewhere" / "c.stn",
        root / "songs_beside" / "a.stn",
    ):
        path.write_text("data")
    (root / "link_songs").symlink_to(root / "songs", target_is_directory=True)
    (root / "link_a.stn").symlink_to(root / "songs" / "a.stn")
    (root / "songs" / "link_out").symlink_to(root / "elsewhere", target_is_directory=True)


@requires_symlinks
class TestWhatARemovalTakes:
    """A removal takes a path exactly where removing the entry leaves no file at that path."""

    @pytest.mark.parametrize(
        ("removed", "path", "taken"),
        [
            ("songs", "songs/a.stn", True),
            ("songs", "songs/takes/b.stn", True),
            ("songs", "link_songs/a.stn", True),
            ("songs", "songs/link_out/c.stn", True),
            ("songs", "elsewhere/c.stn", False),
            ("songs", "songs_beside/a.stn", False),
            ("link_songs", "songs/a.stn", False),
            ("link_songs", "link_songs/a.stn", True),
            ("link_a.stn", "songs/a.stn", False),
            ("link_a.stn", "link_a.stn", True),
            ("songs/a.stn", "link_a.stn", True),
            ("songs/a.stn", "songs/../songs/a.stn", True),
            ("elsewhere", "songs/link_out/c.stn", True),
            ("songs/link_out", "elsewhere/c.stn", False),
        ],
    )
    def test_the_answer_matches_what_the_removal_leaves(
        self,
        tmp_path: Path,
        removed: str,
        path: str,
        taken: bool,
    ) -> None:
        _tree(tmp_path)

        predicted = removal_takes(tmp_path / removed, tmp_path / path)
        remove_path(tmp_path / removed)

        assert (predicted, not (tmp_path / path).exists()) == (taken, taken)

    def test_a_relative_spelling_answers_as_its_absolute_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _tree(tmp_path)
        monkeypatch.chdir(tmp_path)

        answers: Tuple[bool, bool] = (
            removal_takes(Path("link_songs"), tmp_path / "link_songs" / "a.stn"),
            removal_takes(tmp_path / "link_songs", Path("songs") / "a.stn"),
        )

        assert answers == (True, False)
