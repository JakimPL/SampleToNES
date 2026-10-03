import ast
from pathlib import Path
from typing import Final, FrozenSet, Iterator, List

from sampletones_shared.paths.source import REPOSITORY_ROOT
from tests.suite.screens.paths import SCREEN_DRIVER_DIRECTORY, SCREENS_DIRECTORY

SCENARIO_FILE_PREFIX: Final[str] = "test_"
SCREEN_TIER_DIRECTORIES: Final[List[Path]] = [SCREENS_DIRECTORY, SCREEN_DRIVER_DIRECTORY]
NOT_YET_REORGANIZED: Final[FrozenSet[str]] = frozenset(
    {
        "tests/screens/application/test_old_files.py",
        "tests/screens/application/test_restart.py",
        "tests/screens/exports/test_import.py",
        "tests/screens/exports/test_progress.py",
        "tests/screens/interface/test_dialog_sweep.py",
        "tests/screens/main/test_list.py",
        "tests/screens/main/test_row_settings.py",
        "tests/screens/prompts/test_every_door.py",
        "tests/screens/sequencer/test_history.py",
        "tests/suite/screens/application.py",
        "tests/suite/screens/boundaries/dialogs.py",
        "tests/suite/screens/dearpygui/display.py",
    }
)


def screen_tier_modules() -> Iterator[Path]:
    for directory in SCREEN_TIER_DIRECTORIES:
        yield from sorted(directory.rglob("*.py"))


def relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def constants_after_code(path: Path) -> List[int]:
    """The lines of module-level assignments that follow the module's first function or class."""
    lines: List[int] = []
    code_started = False
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            code_started = True
        elif code_started and isinstance(node, (ast.Assign, ast.AnnAssign)):
            lines.append(node.lineno)

    return lines


def imported_scenario_modules(path: Path) -> Iterator[str]:
    """Every scenario file (``test_*.py``) that ``path`` imports by its absolute name."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            if node.module.rsplit(".", 1)[-1].startswith(SCENARIO_FILE_PREFIX):
                yield node.module


class TestTheScreenTierLayout:
    """The screen tier's modules read the same way: constants under the imports, packages that import, scenarios that stand alone."""

    def test_constants_stand_under_the_imports(self) -> None:
        offenders = {
            relative(path): constants_after_code(path)
            for path in screen_tier_modules()
            if relative(path) not in NOT_YET_REORGANIZED and constants_after_code(path)
        }

        assert offenders == {}

    def test_every_folder_of_modules_is_a_package(self) -> None:
        folders = {path.parent for path in screen_tier_modules()}

        assert [relative(folder) for folder in sorted(folders) if not (folder / "__init__.py").exists()] == []

    def test_no_module_imports_a_scenario_file(self) -> None:
        importers = {
            relative(path): list(imported_scenario_modules(path))
            for path in screen_tier_modules()
            if list(imported_scenario_modules(path))
        }

        assert importers == {}

    def test_the_list_of_modules_not_yet_reorganized_names_files_that_still_need_it(self) -> None:
        finished = [
            entry
            for entry in sorted(NOT_YET_REORGANIZED)
            if not (REPOSITORY_ROOT / entry).exists() or not constants_after_code(REPOSITORY_ROOT / entry)
        ]

        assert finished == []
