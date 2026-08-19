from pathlib import Path
from typing import Final

from sampletones_shared.meta.import_boundary.rule import BoundaryRule
from tests.suite.source import write_module

FORBIDDEN: Final[str] = "from other_package.module import Thing\n"
CONTRACT: Final[str] = "from other_package.contract import Result\n"
ALLOWED: Final[str] = "from package.inner import Helper\n"

RULE: Final[BoundaryRule] = BoundaryRule(
    root="package",
    pattern="logic/**/*.py",
    forbidden=("other_package", "third_package"),
    contracts=("other_package.contract",),
)


class TestBoundaryViolations:
    """The imports one module takes past the boundary around it."""

    def test_a_forbidden_import_is_named_by_the_prefix_it_crosses(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "direct.py", FORBIDDEN)

        assert [violation.kind for violation in RULE.violations(path)] == ["other_package"]

    def test_the_report_names_the_line_the_import_sits_on(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "direct.py", f"{ALLOWED}{FORBIDDEN}")

        assert RULE.violations(path)[0].location == f"{path}:2: {FORBIDDEN.strip()}"

    def test_a_contract_module_stays_reachable(self, tmp_path: Path) -> None:
        """A layer reads another layer's data contract while its implementation stays out of reach."""
        path = write_module(tmp_path, "direct.py", CONTRACT)

        assert RULE.violations(path) == []

    def test_an_allowed_import_reports_nothing(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "direct.py", ALLOWED)

        assert RULE.violations(path) == []

    def test_a_module_importing_nothing_reports_nothing(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "direct.py", "VALUE = 1\n")

        assert RULE.violations(path) == []

    def test_one_import_is_reported_once(self, tmp_path: Path) -> None:
        """An import crosses one boundary, so the first prefix it matches names it."""
        rule = BoundaryRule(
            root=RULE.root,
            pattern=RULE.pattern,
            forbidden=("other_package", "other_package.module"),
        )
        path = write_module(tmp_path, "direct.py", FORBIDDEN)

        assert len(rule.violations(path)) == 1

    def test_every_forbidden_import_is_reported_in_line_order(self, tmp_path: Path) -> None:
        body = f"{FORBIDDEN}{ALLOWED}from third_package.module import Other\n"
        path = write_module(tmp_path, "direct.py", body)

        assert [violation.kind for violation in RULE.violations(path)] == ["other_package", "third_package"]
