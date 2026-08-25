from pathlib import Path
from typing import Final

from sampletones_shared.meta.import_boundary.scope import rule_modules
from tests.suite.source import swept_paths, write_module

LOGIC_PATTERN: Final[str] = "logic/**/*.py"
BODY: Final[str] = "from package.inner import Helper\n"


class TestRuleModules:
    """The modules one glob reaches, held to the tree the sweep reads."""

    def test_a_module_directly_under_the_rule_directory_is_reached(self, tmp_path: Path) -> None:
        """`logic/**/*.py` names `logic/direct.py` as surely as `logic/inner/deep.py`."""
        direct = write_module(tmp_path / "logic", "direct.py", BODY)

        assert rule_modules(tmp_path, LOGIC_PATTERN, (), swept_paths(tmp_path), None) == [direct.resolve()]

    def test_a_module_nested_under_the_rule_directory_is_reached(self, tmp_path: Path) -> None:
        deep = write_module(tmp_path / "logic" / "inner", "deep.py", BODY)

        assert rule_modules(tmp_path, LOGIC_PATTERN, (), swept_paths(tmp_path), None) == [deep.resolve()]

    def test_a_module_outside_the_rule_directory_stays_aside(self, tmp_path: Path) -> None:
        write_module(tmp_path / "services", "conversion.py", BODY)

        assert rule_modules(tmp_path, LOGIC_PATTERN, (), swept_paths(tmp_path), None) == []

    def test_a_module_a_nested_rule_owns_is_left_to_it(self, tmp_path: Path) -> None:
        direct = write_module(tmp_path / "logic", "direct.py", BODY)
        write_module(tmp_path / "logic" / "inner", "deep.py", BODY)

        reached = rule_modules(tmp_path, LOGIC_PATTERN, ("logic/inner/**/*.py",), swept_paths(tmp_path), None)

        assert reached == [direct.resolve()]

    def test_a_selection_narrows_the_rule_to_the_files_it_names(self, tmp_path: Path) -> None:
        named = write_module(tmp_path / "logic", "named.py", BODY)
        write_module(tmp_path / "logic", "other.py", BODY)

        reached = rule_modules(tmp_path, LOGIC_PATTERN, (), swept_paths(tmp_path), {named.resolve()})

        assert reached == [named.resolve()]

    def test_the_modules_are_reported_in_path_order(self, tmp_path: Path) -> None:
        second = write_module(tmp_path / "logic", "second.py", BODY)
        first = write_module(tmp_path / "logic", "first.py", BODY)

        reached = rule_modules(tmp_path, LOGIC_PATTERN, (), swept_paths(tmp_path), None)

        assert reached == [first.resolve(), second.resolve()]
