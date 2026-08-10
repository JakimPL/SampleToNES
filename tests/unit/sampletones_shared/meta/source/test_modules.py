import ast
import re
from pathlib import Path
from typing import Final

import pytest

from sampletones_shared.meta.source.modules import (
    discover_modules,
    is_visible,
    module_name,
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


class TestModuleName:
    def test_a_module_is_named_by_the_path_reaching_it(self) -> None:
        assert module_name(Path("/src/package/inner/module.py"), Path("/src")) == "package.inner.module"

    def test_a_module_at_the_root_is_named_alone(self) -> None:
        assert module_name(Path("/src/module.py"), Path("/src")) == "module"

    def test_an_initializer_names_the_package_holding_it(self) -> None:
        assert module_name(Path("/src/package/inner/__init__.py"), Path("/src")) == "package.inner"

    def test_a_file_outside_the_root_raises(self) -> None:
        with pytest.raises(ValueError):
            module_name(Path("/elsewhere/module.py"), Path("/src"))


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


class TestSweptRoots:
    """A sweep reading nothing leaves a check reporting nothing, which reads as a clean tree."""

    def test_an_absent_root_raises(self, tmp_path: Path) -> None:
        with pytest.raises(NotADirectoryError):
            source_paths([tmp_path / "absent"])

    def test_a_root_naming_a_module_raises(self, tmp_path: Path) -> None:
        """A package resource resolves to `__init__.py`, which a sweep reads nothing under."""
        path = write_module(tmp_path, "first.py", MODULE_BODY)
        with pytest.raises(NotADirectoryError):
            source_paths([path])

    def test_a_root_beside_a_readable_one_is_held_to_the_same_rule(self, tmp_path: Path) -> None:
        write_module(tmp_path / "package", "first.py", MODULE_BODY)
        with pytest.raises(NotADirectoryError):
            source_paths([tmp_path / "package", tmp_path / "absent"])

    def test_roots_holding_no_source_raise(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            source_paths([tmp_path])

    def test_the_report_names_the_root_it_read_nothing_under(self, tmp_path: Path) -> None:
        """A Windows root spells separators and drive letters a regex reads as escapes, so the path
        is quoted before it is matched."""
        with pytest.raises(FileNotFoundError, match=re.escape(str(tmp_path))):
            source_paths([tmp_path])


class TestDiscoverModules:
    def test_every_module_found_is_parsed(self, tmp_path: Path) -> None:
        write_module(tmp_path, "first.py", MODULE_BODY)
        write_module(tmp_path / "inner", "second.py", MODULE_BODY)
        modules = discover_modules([tmp_path])
        assert [module.path.name for module in modules] == ["first.py", "second.py"]

    def test_a_root_holding_no_module_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            discover_modules([tmp_path])
