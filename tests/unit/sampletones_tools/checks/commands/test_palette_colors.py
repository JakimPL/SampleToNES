from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_application.paths import PALETTES_DIRECTORY
from sampletones_shared.paths.resources import CONFIG_DIRECTORY
from sampletones_tools.checks import palette_colors
from sampletones_tools.checks.palette_colors import APPLICATION_PACKAGE, ColorFinding

GUARD: Final[str] = "sampletones_tools.checkout.require_checkout"


class RecordedCheck:
    def __init__(self) -> None:
        self.checked: List[Tuple[Path, Path, Path]] = []

    def __call__(self, package: Path, config: Path, palettes: Path) -> List[ColorFinding]:
        self.checked.append((package, config, palettes))
        return []


@pytest.fixture(name="check")
def check_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedCheck:
    recorded = RecordedCheck()
    guarded: List[str] = []
    monkeypatch.setattr(palette_colors, "check_colors", recorded)
    monkeypatch.setattr(GUARD, guarded.append)
    return recorded


class TestPaletteColorsCommand:
    def test_the_shipped_trees_are_checked_when_none_is_named(self, check: RecordedCheck) -> None:
        assert dispatch(COMMANDS, ["check", "palette-colors"]) == 0
        assert check.checked == [(APPLICATION_PACKAGE, CONFIG_DIRECTORY, PALETTES_DIRECTORY)]

    def test_the_trees_named_are_the_ones_checked(self, check: RecordedCheck, tmp_path: Path) -> None:
        package = tmp_path / "package"
        config = tmp_path / "config"
        palettes = tmp_path / "palettes"

        status = dispatch(
            COMMANDS,
            [
                "check",
                "palette-colors",
                "--package",
                str(package),
                "--config-directory",
                str(config),
                "--palettes",
                str(palettes),
            ],
        )

        assert status == 0
        assert check.checked == [(package, config, palettes)]
