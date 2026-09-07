from dataclasses import dataclass
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_shared.meta.source.modules import SourceModule
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script
from tests.suite.source import parse_source

check_rendered_literals = load_script("checks/rendered_literals.py")

CASE_MODULE: Final[Path] = Path("tests/unit/test_card.py")


def locations(source: str) -> List[str]:
    module = SourceModule(path=CASE_MODULE, tree=parse_source(source))
    return [finding.location for finding in check_rendered_literals.findings([module])]


def renderings(source: str) -> List[str]:
    module = SourceModule(path=CASE_MODULE, tree=parse_source(source))
    return [finding.rendering for finding in check_rendered_literals.findings([module])]


class TestWhatIsReported(BaseTestSuite):
    """A case rendering a value and holding the result against a written-out string.

    Which rendering it used is named in the report, so a reader meets the expression the finding is
    about rather than hunting for it on the line.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        source: str
        expected: str

    test_cases = (
        TestCase(
            label="rendered_on_the_left",
            source='assert str(view.path) == "/audio/kick.wav"\n',
            expected="str()",
        ),
        TestCase(
            label="rendered_on_the_right",
            source='assert "/audio/kick.wav" == str(view.path)\n',
            expected="str()",
        ),
        TestCase(
            label="rendered_by_a_template",
            source='assert f"{view.path}" == "/audio/kick.wav"\n',
            expected="an f-string",
        ),
        TestCase(
            label="rendered_inside_a_chain",
            source='assert "a" == str(view.path) == other\n',
            expected="str()",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_is_reported_where_it_sits(self, test_case: TestCase) -> None:
        assert locations(test_case.source) == [f"{CASE_MODULE}:1"]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_rendering_it_used_is_named(self, test_case: TestCase) -> None:
        assert renderings(test_case.source) == [test_case.expected]


class TestWhatIsLeftAlone(BaseTestSuite):
    """A case comparing values, or rendering both sides, states no one platform's answer.

    A call the case makes is left alone whatever it returns, which is what keeps the check to the
    one shape it is about rather than to every comparison holding a string.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        source: str

    test_cases = (
        TestCase(label="a_path_against_a_path", source='assert view.path == Path("/audio/kick.wav")\n'),
        TestCase(label="both_sides_rendered", source="assert str(view.path) == str(expected)\n"),
        TestCase(label="a_value_against_a_literal", source='assert view.name == "kick"\n'),
        TestCase(
            label="another_call_against_a_literal",
            source='assert abbreviate_channel_names([PULSE1]) == "P"\n',
        ),
        TestCase(label="a_template_holding_no_value", source='assert f"kick" == "kick"\n'),
        TestCase(label="a_fragment_read_out_of_a_rendering", source='assert "kick" in str(view.path)\n'),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_is_passed_over(self, test_case: TestCase) -> None:
        assert locations(test_case.source) == []


class TestMain:
    def test_no_case_in_the_repository_holds_rendered_text_against_a_literal(self) -> None:
        assert check_rendered_literals.main([]) == 0

    def test_a_case_that_does_is_reported_where_it_sits(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cases = tmp_path / "cases"
        cases.mkdir()
        module = cases / "test_card.py"
        module.write_text(
            'def test_it() -> None:\n    assert str(view.path) == "/audio/kick.wav"\n',
            encoding="utf-8",
        )

        exit_code = check_rendered_literals.main(["--tests", str(cases)])

        assert exit_code == 1
        assert f"{module}:2" in capsys.readouterr().err
