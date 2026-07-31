import tempfile
from pathlib import Path
from typing import Final

import pytest

from sampletones_shared.utils.system.filesystem import remove_path


def _symlinks_are_permitted() -> bool:
    """Reports whether this machine lets an unprivileged process create a symlink.

    Windows grants the privilege only under Developer Mode or elevation, so the probe
    creates one in a throwaway directory and reads the answer from the attempt.
    """
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        try:
            (root / "probe").symlink_to(root, target_is_directory=True)
        except OSError:
            return False

    return True


SYMLINKS_PERMITTED: Final[bool] = _symlinks_are_permitted()


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

    @pytest.mark.skipif(not SYMLINKS_PERMITTED, reason="creating a symlink requires a privilege this machine withholds")
    def test_removes_directory_symlink_without_touching_target(self, tmp_path: Path) -> None:
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
