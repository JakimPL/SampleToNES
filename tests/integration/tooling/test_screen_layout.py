import ast
from pathlib import Path
from typing import Final, Iterator, List

from automation.paths import AUTOMATION_DIRECTORY
from sampletones_shared.paths.source import REPOSITORY_ROOT

SCENARIO_FILE_PREFIX: Final[str] = "test_"
CASES_MODULE: Final[str] = "cases.py"
SCENARIOS_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "tests" / "screens"
MATERIAL_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "tests" / "suite" / "screens"
SCREEN_TIER_DIRECTORIES: Final[List[Path]] = [SCENARIOS_DIRECTORY, MATERIAL_DIRECTORY, AUTOMATION_DIRECTORY]


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
            if path.name != CASES_MODULE and constants_after_code(path)
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
