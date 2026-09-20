import csv
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_shared.exceptions.project import NotAValidArchiveError
from sampletones_shared.utils.tables import Table
from sampletones_tools.codec.study.manifest import StudyManifest, StudySource
from sampletones_tools.codec.study.plan import StudyPlan, plan_study
from sampletones_tools.codec.study.report import rows as songs
from sampletones_tools.codec.study.report import verdicts
from sampletones_tools.codec.study.report.run import MANIFEST_JSON, REPORT_CSV, REPORT_MARKDOWN, VERDICTS_CSV
from sampletones_tools.codec.study.session import run_study

VARIANT: Final[str] = "wide-hold"
PACKED_VARIANT: Final[str] = "packed-table"
LENGTHEN_SECONDS: Final[int] = 2


def _read_csv(path: Path) -> List[List[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


@pytest.fixture(name="plan")
def plan_fixture(integration_project: Project, tmp_path: Path) -> StudyPlan:
    project = tmp_path / "synthetic.stp"
    ProjectContainer.save(integration_project, project)
    return plan_study(
        StudyManifest(
            projects=(StudySource.at(project),),
            reconstructions=(),
            lengthen_seconds=LENGTHEN_SECONDS,
            variants=(VARIANT,),
        )
    )


class TestStudyRun:
    def test_a_run_writes_its_tables_and_the_manifest_that_repeats_it(self, plan: StudyPlan, tmp_path: Path) -> None:
        directory = run_study(plan, tmp_path / "run")

        assert StudyManifest.load(directory / MANIFEST_JSON) == plan.manifest

        header, *measured = _read_csv(directory / REPORT_CSV)
        assert tuple(header) == songs.COLUMNS
        assert {row[header.index("variant")] for row in measured} >= {variant.name for variant in plan.variants}

        verdict_header, *verdict_rows = _read_csv(directory / VERDICTS_CSV)
        assert tuple(verdict_header) == verdicts.COLUMNS

        markdown = (directory / REPORT_MARKDOWN).read_text(encoding="utf-8").split("\n")
        table = Table(columns=verdicts.COLUMNS, rows=tuple(tuple(row) for row in verdict_rows)).markdown_lines()
        start = markdown.index(table[0])
        assert markdown[start : start + len(table)] == table

    def test_a_packed_plane_run_reads_back_as_the_song_it_was_written_from(
        self,
        integration_project: Project,
        tmp_path: Path,
    ) -> None:
        """A run refuses a variant whose streams do not play back, so completing is the assertion."""
        project = tmp_path / "packed.stp"
        ProjectContainer.save(integration_project, project)
        plan = plan_study(
            StudyManifest(
                projects=(StudySource.at(project),),
                reconstructions=(),
                lengthen_seconds=LENGTHEN_SECONDS,
                variants=(PACKED_VARIANT,),
            )
        )

        directory = run_study(plan, tmp_path / "run")

        header, *measured = _read_csv(directory / REPORT_CSV)
        variant = header.index("variant")
        assert {row[variant] for row in measured} >= {PACKED_VARIANT}

    def test_a_source_that_fails_to_read_leaves_the_output_untouched(self, tmp_path: Path) -> None:
        broken = tmp_path / "broken.stp"
        broken.write_bytes(b"")
        output = tmp_path / "run"
        plan = plan_study(
            StudyManifest(
                projects=(StudySource.at(broken),),
                reconstructions=(),
                lengthen_seconds=LENGTHEN_SECONDS,
                variants=(VARIANT,),
            )
        )

        with pytest.raises(NotAValidArchiveError):
            run_study(plan, output)

        assert not output.exists()
