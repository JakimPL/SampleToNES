import ast
import sys
from pathlib import Path
from typing import Final, FrozenSet, Iterator

from tests.suite.screens.paths import DEARPYGUI_LAYER_DIRECTORY

LAYER_PACKAGE: Final[str] = "tests.suite.screens.dearpygui"
MODULE_SEPARATOR: Final[str] = "."
THIRD_PARTY: Final[FrozenSet[str]] = frozenset({"dearpygui", "pytest", "pyvirtualdisplay", "Xlib"})


def imported_modules(path: Path) -> Iterator[str]:
    """Every module ``path`` imports by its absolute name."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            yield node.module


def is_allowed(module: str) -> bool:
    top = module.split(MODULE_SEPARATOR, 1)[0]
    return (
        top in sys.stdlib_module_names
        or top in THIRD_PARTY
        or module == LAYER_PACKAGE
        or module.startswith(LAYER_PACKAGE + MODULE_SEPARATOR)
    )


class TestTheDearPyGuiLayer:
    """The screen tier's DearPyGui layer knows DearPyGui and pytest, and nothing of SampleToNES.

    The layer drives any DearPyGui application, and SampleToNES builds on it from outside, so the
    layer moves to a project of its own as it stands the day a second application wants it.
    """

    def test_every_import_is_dearpygui_pytest_x11_or_the_standard_library(self) -> None:
        strays = [
            f"{path.name} imports {module}"
            for path in sorted(DEARPYGUI_LAYER_DIRECTORY.rglob("*.py"))
            for module in imported_modules(path)
            if not is_allowed(module)
        ]

        assert strays == []

    def test_the_layer_holds_modules_to_read(self) -> None:
        assert any(DEARPYGUI_LAYER_DIRECTORY.rglob("*.py"))
