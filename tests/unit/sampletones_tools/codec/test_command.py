import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Optional, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.codec.command import DEFAULT_LENGTHEN_SECONDS, NO_SOURCE
from sampletones_tools.codec.report.session import CompressionReport
from sampletones_tools.codec.study.plan import StudyPlan
from sampletones_tools.codec.study.variants.production import BASELINE_NAME
from sampletones_tools.codec.study.variants.registry import EVERY_VARIANT
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.files import empty_file

RUNNER: Final[str] = "sampletones_tools.codec.study.session.run_study"
REPORTER: Final[str] = "sampletones_tools.codec.report.session.run_report"


class RecordedStudy:
    def __init__(self) -> None:
        self.runs: List[Tuple[StudyPlan, Optional[Path]]] = []

    def __call__(self, plan: StudyPlan, output: Optional[Path]) -> Path:
        self.runs.append((plan, output))
        return output if output is not None else Path("run")


@dataclass(frozen=True)
class StudySources:
    project: Path
    reconstruction: Path


@pytest.fixture(name="study")
def study_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedStudy:
    recorded = RecordedStudy()
    monkeypatch.setattr(RUNNER, recorded)
    return recorded


@pytest.fixture(name="sources")
def sources_fixture(tmp_path: Path) -> StudySources:
    reconstruction = tmp_path / "stems" / "two"
    reconstruction.mkdir(parents=True)
    return StudySources(project=empty_file(tmp_path / "songs", "one.stp"), reconstruction=reconstruction)


class TestCodecReport:
    def test_the_report_is_written_into_the_output_and_its_tables_are_printed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        outputs: List[Path] = []

        def run_report(output: Path) -> CompressionReport:
            outputs.append(output)
            return CompressionReport(
                entries=(),
                encodings=(),
                csv_path=output / "report.csv",
                markdown_path=output / "report.md",
            )

        monkeypatch.setattr(REPORTER, run_report)

        assert dispatch(COMMANDS, ["codec", "report", "-o", str(tmp_path)]) == 0
        assert outputs == [tmp_path]
        assert capsys.readouterr().out.splitlines() == [
            f"Wrote {tmp_path / 'report.csv'}",
            f"Wrote {tmp_path / 'report.md'}",
        ]

    def test_the_output_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["codec", "report"])

        assert leaving.value.code == 2


class TestCodecStudy:
    def test_the_sources_and_the_sweep_are_read_from_the_options(
        self,
        study: RecordedStudy,
        sources: StudySources,
        tmp_path: Path,
    ) -> None:
        status = dispatch(
            COMMANDS,
            [
                "codec",
                "study",
                "--project",
                str(sources.project),
                "--reconstruction",
                str(sources.reconstruction),
                "--variants",
                "wide-hold",
                "--lengthen",
                "30",
                "-o",
                str(tmp_path),
            ],
        )

        assert status == 0
        plan, output = study.runs[0]
        assert [source.path for source in plan.manifest.projects] == [sources.project]
        assert [source.path for source in plan.manifest.reconstructions] == [sources.reconstruction]
        assert plan.manifest.variants == ("wide-hold",)
        assert [variant.name for variant in plan.variants] == [BASELINE_NAME, "wide-hold"]
        assert plan.manifest.lengthen_seconds == 30
        assert output == tmp_path

    def test_a_run_naming_no_source_is_refused_with_the_way_to_name_one(self, study: RecordedStudy) -> None:
        with pytest.raises(SystemExit, match=re.escape(NO_SOURCE)):
            dispatch(COMMANDS, ["codec", "study"])

        assert all(flag in NO_SOURCE for flag in ("--project", "--reconstruction", "--manifest"))
        assert study.runs == []

    def test_the_lengthening_defaults_to_its_constant(self, study: RecordedStudy, sources: StudySources) -> None:
        assert dispatch(COMMANDS, ["codec", "study", "--project", str(sources.project)]) == 0
        plan, output = study.runs[0]
        assert plan.manifest.lengthen_seconds == DEFAULT_LENGTHEN_SECONDS
        assert plan.manifest.variants == (EVERY_VARIANT,)
        assert output is None

    def test_an_action_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["codec"])

        assert leaving.value.code == 2


class TestRefusedStudies(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        argv: Tuple[str, ...]
        refusal: str

    test_cases = (
        TestCase(label="an unknown variant", argv=("--variants", "bogus"), refusal="No variant is called bogus"),
        TestCase(label="no lengthening", argv=("--lengthen", "0"), refusal="lengthen_seconds"),
        TestCase(label="a missing manifest", argv=("--manifest", "{directory}/absent.json"), refusal="No manifest at"),
        TestCase(label="a missing project", argv=("--project", "{directory}/absent.stp"), refusal="No file at"),
        TestCase(label="a broken manifest", argv=("--manifest", "{directory}/broken.json"), refusal="JSON"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_run_asking_the_impossible_is_refused_in_one_line_before_it_starts(
        self,
        study: RecordedStudy,
        sources: StudySources,
        tmp_path: Path,
        test_case: TestCase,
    ) -> None:
        (tmp_path / "broken.json").write_text("{", encoding="utf-8")
        argv = [argument.format(directory=tmp_path) for argument in test_case.argv]

        with pytest.raises(SystemExit, match=test_case.refusal) as leaving:
            dispatch(COMMANDS, ["codec", "study", "--project", str(sources.project), *argv])

        assert len(str(leaving.value).splitlines()) == 1
        assert study.runs == []
