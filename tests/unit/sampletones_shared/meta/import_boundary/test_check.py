from pathlib import Path
from typing import Final, Tuple

import pytest

from sampletones_shared.meta.import_boundary.check import check_boundaries
from sampletones_shared.meta.import_boundary.rule import BoundaryRule
from sampletones_shared.meta.import_boundary.token import TokenRule
from tests.suite.source import write_module

FORBIDDEN: Final[str] = "from other_package.module import Thing\n"
ALLOWED: Final[str] = "from package.inner import Helper\n"
SPELLING: Final[str] = "dpg.add_group(parent=SUF_PANEL_LEFT)\n"

RULES: Final[Tuple[BoundaryRule, ...]] = (
    BoundaryRule(
        root="package",
        pattern="logic/**/*.py",
        forbidden=("other_package",),
    ),
    BoundaryRule(
        root="package",
        pattern="nested/**/*.py",
        forbidden=("other_package",),
        excluding=("nested/inner/**/*.py",),
    ),
)

TOKEN_RULES: Final[Tuple[TokenRule, ...]] = (
    TokenRule(
        root="package",
        pattern="ui/**/*.py",
        forbidden=r"\bSUF_PANEL_",
        message="ui stays clear of a column suffix",
    ),
)


class TestCheckBoundaries:
    """Every rule read over one tree, from the sweep to the report."""

    def test_a_forbidden_import_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / "package" / "logic", "direct.py", FORBIDDEN)

        violations = check_boundaries(tmp_path, RULES, TOKEN_RULES, None)

        assert [violation.kind for violation in violations] == ["other_package"]

    def test_an_allowed_import_reports_nothing(self, tmp_path: Path) -> None:
        write_module(tmp_path / "package" / "logic", "direct.py", ALLOWED)

        assert check_boundaries(tmp_path, RULES, TOKEN_RULES, None) == []

    def test_a_module_outside_every_rule_stays_unchecked(self, tmp_path: Path) -> None:
        write_module(tmp_path / "package" / "services", "conversion.py", FORBIDDEN)

        assert check_boundaries(tmp_path, RULES, TOKEN_RULES, None) == []

    def test_a_module_a_nested_rule_owns_is_left_to_it(self, tmp_path: Path) -> None:
        write_module(tmp_path / "package" / "nested" / "inner", "deep.py", FORBIDDEN)

        assert check_boundaries(tmp_path, RULES, TOKEN_RULES, None) == []

    def test_a_forbidden_spelling_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / "package" / "ui", "left.py", SPELLING)

        violations = check_boundaries(tmp_path, RULES, TOKEN_RULES, None)

        assert [violation.kind for violation in violations] == ["ui stays clear of a column suffix"]

    def test_the_boundary_rules_are_reported_before_the_token_rules(self, tmp_path: Path) -> None:
        write_module(tmp_path / "package" / "ui", "left.py", SPELLING)
        write_module(tmp_path / "package" / "logic", "direct.py", FORBIDDEN)

        violations = check_boundaries(tmp_path, RULES, TOKEN_RULES, None)

        assert [violation.kind for violation in violations] == [
            "other_package",
            "ui stays clear of a column suffix",
        ]

    def test_a_selection_narrows_the_check(self, tmp_path: Path) -> None:
        checked = write_module(tmp_path / "package" / "logic", "checked.py", FORBIDDEN)
        write_module(tmp_path / "package" / "logic", "other.py", FORBIDDEN)

        violations = check_boundaries(tmp_path, RULES, TOKEN_RULES, {checked.resolve()})

        assert len(violations) == 1


class TestSweptRoots:
    """A root the sweep reads nothing under stops the check, where it would report a clean tree."""

    def test_a_root_holding_no_module_stops_the_check(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            check_boundaries(tmp_path, RULES, TOKEN_RULES, None)

    def test_an_absent_root_stops_the_check(self, tmp_path: Path) -> None:
        with pytest.raises(NotADirectoryError):
            check_boundaries(tmp_path / "absent", RULES, TOKEN_RULES, None)
