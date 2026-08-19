from pathlib import Path
from typing import Final

from sampletones_shared.meta.import_boundary.token import TokenRule
from tests.suite.source import write_module

MESSAGE: Final[str] = "a panel receives its parent through create_panel(parent)"

RULE: Final[TokenRule] = TokenRule(
    root="package",
    pattern="ui/**/*.py",
    forbidden=r"\bSUF_PANEL_",
    message=MESSAGE,
)


class TestTokenViolations:
    """The lines of one module that write a spelling the rule keeps out."""

    def test_the_forbidden_spelling_is_reported_with_the_rules_message(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "left.py", "dpg.add_group(parent=SUF_PANEL_LEFT)\n")

        assert [violation.kind for violation in RULE.violations(path)] == [MESSAGE]

    def test_the_report_names_the_line_the_spelling_sits_on(self, tmp_path: Path) -> None:
        line = "dpg.add_group(parent=SUF_PANEL_LEFT)"
        path = write_module(tmp_path, "left.py", f"VALUE = 1\n{line}\n")

        assert RULE.violations(path)[0].location == f"{path}:2: {line}"

    def test_a_module_clear_of_the_spelling_reports_nothing(self, tmp_path: Path) -> None:
        path = write_module(tmp_path, "left.py", "dpg.add_group(parent=parent)\n")

        assert RULE.violations(path) == []

    def test_every_line_writing_the_spelling_is_reported(self, tmp_path: Path) -> None:
        body = "first = SUF_PANEL_LEFT\nsecond = 1\nthird = SUF_PANEL_RIGHT\n"
        path = write_module(tmp_path, "left.py", body)

        assert len(RULE.violations(path)) == 2
