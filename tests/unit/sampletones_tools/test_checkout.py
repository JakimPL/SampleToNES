from pathlib import Path

import pytest

from sampletones_tools import checkout
from sampletones_tools.checkout import is_checkout, require_checkout

COMMAND = "check import-boundary --all"


class TestIsCheckout:
    def test_the_project_file_beside_the_source_tree_makes_a_checkout(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "src").mkdir()

        assert is_checkout(tmp_path)

    def test_an_installed_copy_is_no_checkout(self, tmp_path: Path) -> None:
        (tmp_path / "site-packages").mkdir()

        assert not is_checkout(tmp_path)


class TestRequireCheckout:
    def test_the_repository_passes(self) -> None:
        require_checkout(COMMAND)

    def test_outside_a_checkout_the_command_is_refused_with_the_way_to_run_it(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(checkout, "REPOSITORY_ROOT", tmp_path)

        with pytest.raises(SystemExit, match=f"uv run sampletones {COMMAND}"):
            require_checkout(COMMAND)
