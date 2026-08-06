import ast
from pathlib import Path
from typing import Final

import pytest

from sampletones_shared.meta.source.modules import (
    discover_modules,
    is_visible,
    parse_module,
    source_paths,
)

MODULE_BODY: Final[str] = "TAG_MAIN_WINDOW = 'main.window'\n"
BYTE_ORDER_MARK: Final[str] = "\ufeff"


def write_module(directory: Path, name: str, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


class TestParseModule:
    def test_a_module_parses_into_a_tree(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "plain.py", MODULE_BODY)
        module = parse_module(path)
        assert isinstance(module.tree, ast.Module)

    def test_the_path_travels_with_the_tree(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "plain.py", MODULE_BODY)
        assert parse_module(path).path == path

    def test_a_byte_order_marked_module_parses(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "marked.py", BYTE_ORDER_MARK + MODULE_BODY)
        module = parse_module(path)
        assert len(module.tree.body) == 1

    def test_source_python_rejects_raises(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "broken.py", "def missing(\n")
        with pytest.raises(SyntaxError):
            parse_module(path)

    def test_a_location_names_the_path_and_the_line(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "plain.py", f"\n\n{MODULE_BODY}")
        module = parse_module(path)
        assert module.location(module.tree.body[0]) == f"{path}:3"


class TestIsVisible:
    def test_a_plain_path_is_visible(self) -> None:
        assert is_visible(Path("src/sampletones_shared/meta/source/modules.py"))

    def test_a_hidden_directory_hides_the_path(self) -> None:
        assert not is_visible(Path(".venv/lib/python3.12/ast.py"))

    def test_a_hidden_file_is_hidden(self) -> None:
        assert not is_visible(Path("src/.generated.py"))


class TestSourcePaths:
    def test_every_module_under_a_root_is_found(self, tmp_path: Path) -> None:
        first = write_module(tmp_path / "package", "first.py", MODULE_BODY)
        second = write_module(tmp_path / "package" / "inner", "second.py", MODULE_BODY)
        assert source_paths([tmp_path]) == sorted([first, second])

    def test_a_module_under_two_roots_is_listed_once(self, tmp_path: Path) -> None:
        path = write_module(tmp_path / "package", "first.py", MODULE_BODY)
        assert source_paths([tmp_path, tmp_path / "package"]) == [path]

    def test_a_hidden_directory_stays_aside(self, tmp_path: Path) -> None:
        visible = write_module(tmp_path / "package", "first.py", MODULE_BODY)
        write_module(tmp_path / ".cache", "cached.py", MODULE_BODY)
        assert source_paths([tmp_path]) == [visible]

    def test_a_file_of_another_kind_stays_aside(self, tmp_path: Path) -> None:
        visible = write_module(tmp_path, "first.py", MODULE_BODY)
        write_module(tmp_path, "notes.md", "# notes\n")
        assert source_paths([tmp_path]) == [visible]


class TestDiscoverModules:
    def test_every_module_found_is_parsed(self, tmp_path: Path) -> None:
        write_module(tmp_path, "first.py", MODULE_BODY)
        write_module(tmp_path / "inner", "second.py", MODULE_BODY)
        modules = discover_modules([tmp_path])
        assert [module.path.name for module in modules] == ["first.py", "second.py"]
