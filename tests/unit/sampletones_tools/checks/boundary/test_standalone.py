from pathlib import Path
from typing import Final, List

import pytest

from sampletones_tools.checks.boundary.standalone import (
    StandaloneRule,
    check_standalone,
    local_names,
)
from tests.suite.source import write_module

MESSAGE: Final[str] = "a bootstrap script imports the standard library and the tree alone"

RULE: Final[StandaloneRule] = StandaloneRule(
    pattern="**/*.py",
    reserved=("tests",),
    message=MESSAGE,
)

THIRD_PARTY: Final[str] = "import numpy\n"
REACHABLE: Final[str] = (
    "import argparse\n"
    "from pathlib import Path\n"
    "from bootstrap.processes import run\n"
    "import detect_cuda\n"
    "from . import sibling\n"
)


def _tree(root: Path) -> None:
    write_module(root / "bootstrap", "__init__.py", "")
    write_module(root / "bootstrap", "processes.py", "import subprocess\n")
    write_module(root, "detect_cuda.py", "import re\n")


def kinds(root: Path) -> List[str]:
    """What the rule reports over a tree a test builds."""
    return [violation.kind for violation in check_standalone(root, (RULE,), None)]


class TestLocalNames:
    def test_the_modules_and_the_packages_of_the_tree_are_its_names(self, tmp_path: Path) -> None:
        _tree(tmp_path)
        (tmp_path / "runtime_hooks").mkdir()

        assert local_names(tmp_path) == {"bootstrap", "detect_cuda"}


class TestStandaloneViolations:
    """The imports of one script that reach past the standard library and the tree."""

    def test_a_third_party_import_is_reported_with_the_rules_message(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "bundle.py", THIRD_PARTY)

        assert [violation.kind for violation in RULE.violations(path, set())] == [MESSAGE]

    def test_the_standard_library_and_the_tree_stay_reachable(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "bundle.py", REACHABLE)

        assert RULE.violations(path, {"bootstrap", "detect_cuda"}) == []

    def test_the_report_names_the_line_the_import_sits_on(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "bundle.py", f"import sys\n{THIRD_PARTY}")

        assert RULE.violations(path, set())[0].location == f"{path}:2: import numpy"


class TestShadowing:
    """A name in the tree that stands in for a module the tree sits beside."""

    def test_a_standard_library_name_is_reported_once_at_its_first_script(self, tmp_path: Path) -> None:
        first = write_module(tmp_path / "venv", "first.py", "")
        write_module(tmp_path / "venv", "second.py", "")

        reported = RULE.shadowing(tmp_path, [first, tmp_path / "venv" / "second.py"])

        assert [violation.kind for violation in reported] == ["venv stands in for a module the tree sits beside"]
        assert reported[0].location == str(first)

    def test_a_reserved_name_is_reported(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "tests.py", "")

        assert [violation.kind for violation in RULE.shadowing(tmp_path, [path])] == [
            "tests stands in for a module the tree sits beside",
        ]

    def test_a_name_of_the_trees_own_is_left_alone(self, tmp_path: Path) -> None:
        path = write_module(tmp_path / "bootstrap", "venv_build.py", "")

        assert RULE.shadowing(tmp_path, [path]) == []


class TestCheckStandalone:
    """Every rule read over one tree, from the sweep to the report."""

    def test_a_clean_tree_reports_nothing(self, tmp_path: Path) -> None:
        _tree(tmp_path)
        write_module(tmp_path, "bundle.py", REACHABLE)

        assert kinds(tmp_path) == []

    def test_a_script_in_a_subdirectory_is_held_to_the_rule(self, tmp_path: Path) -> None:
        _tree(tmp_path)
        write_module(tmp_path / "ci", "archive.py", THIRD_PARTY)

        assert kinds(tmp_path) == [MESSAGE]

    def test_the_shadowing_names_lead_the_imports(self, tmp_path: Path) -> None:
        _tree(tmp_path)
        write_module(tmp_path, "bundle.py", THIRD_PARTY)
        write_module(tmp_path, "platform.py", "")

        assert kinds(tmp_path) == ["platform stands in for a module the tree sits beside", MESSAGE]

    def test_a_selection_narrows_the_check(self, tmp_path: Path) -> None:
        _tree(tmp_path)
        checked = write_module(tmp_path, "checked.py", THIRD_PARTY)
        write_module(tmp_path, "other.py", THIRD_PARTY)

        assert len(check_standalone(tmp_path, (RULE,), {checked.resolve()})) == 1

    def test_a_tree_holding_no_script_stops_the_check(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            check_standalone(tmp_path, (RULE,), None)
