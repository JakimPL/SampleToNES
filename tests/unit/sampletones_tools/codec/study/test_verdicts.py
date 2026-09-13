from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final, Optional, Tuple

import pytest

from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.compression import PLANE_COUNT
from sampletones_shared.music import Tuning
from sampletones_tools.codec.study.corpus.song import SongGroup, StudySong
from sampletones_tools.codec.study.measure import Encoding, Measurement
from sampletones_tools.codec.study.report.aggregate import group_rows
from sampletones_tools.codec.study.report.verdicts import Verdict, judge, verdict_rows
from sampletones_tools.codec.study.variants.variant import Variant, VariantKind
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TICKS: Final[int] = 4
BASELINE: Final[str] = "baseline"
STREAM: Final[int] = 100


class TestJudge(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        projects: Optional[float]
        reconstructions: Optional[float]
        worst: float
        priced: bool
        expected: Verdict

    test_cases = (
        TestCase(
            label="saving enough over the projects graduates",
            projects=-0.03,
            reconstructions=0.0,
            worst=0.0,
            priced=False,
            expected=Verdict.GRADUATES,
        ),
        TestCase(
            label="saving enough over the reconstructions graduates",
            projects=0.0,
            reconstructions=-0.05,
            worst=-0.02,
            priced=False,
            expected=Verdict.GRADUATES,
        ),
        TestCase(
            label="a token-level price is provisional",
            projects=-0.1,
            reconstructions=-0.1,
            worst=0.0,
            priced=True,
            expected=Verdict.PROVISIONAL,
        ),
        TestCase(
            label="a song growing past the bar rejects the variant",
            projects=-0.1,
            reconstructions=-0.1,
            worst=0.011,
            priced=False,
            expected=Verdict.REJECTED,
        ),
        TestCase(
            label="saving too little rejects the variant",
            projects=-0.029,
            reconstructions=-0.049,
            worst=0.0,
            priced=False,
            expected=Verdict.REJECTED,
        ),
        TestCase(
            label="a group the variant left unmeasured counts for nothing",
            projects=None,
            reconstructions=-0.05,
            worst=0.0,
            priced=False,
            expected=Verdict.GRADUATES,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_rule_answers(self, test_case: TestCase) -> None:
        verdict = judge(
            test_case.projects,
            test_case.reconstructions,
            test_case.worst,
            priced=test_case.priced,
        )

        assert verdict is test_case.expected


def _song(name: str, group: SongGroup) -> StudySong:
    return StudySong(
        name=name,
        group=group,
        source=Path(f"{name}.stp"),
        planes=SongPlanes.from_order(PlaneOrder.across([bytes(TICKS)] * PLANE_COUNT)),
        seeds=(),
        pitches=PitchTable.from_tuning(Tuning()),
    )


def _measurement(
    song: StudySong,
    variant: str,
    streams: int,
) -> Measurement:
    return Measurement(
        song=song,
        variant=variant,
        encoding=Encoding(
            phrases=0,
            dictionary=0,
            streams=(streams,) + (0,) * (PLANE_COUNT - 1),
            seconds=0.0,
            lossless=True,
            written=None,
        ),
    )


def _variant(name: str, kind: VariantKind) -> Variant:
    return Variant(
        name=name,
        hypothesis="H",
        kind=kind,
        note="",
        encode=lambda song: Encoding(
            phrases=0,
            dictionary=0,
            streams=(),
            seconds=0.0,
            lossless=True,
            written=None,
        ),
        needs_seeds=False,
    )


class TestVerdictRows:
    short = _song("short", SongGroup.PROJECT)
    long = _song("long", SongGroup.LONG_PROJECT)
    stem = _song("stem", SongGroup.RECONSTRUCTION)
    variants: Tuple[Variant, ...] = (
        _variant(BASELINE, VariantKind.BASELINE),
        _variant("shrinks", VariantKind.FORMAT),
        _variant("projects-only", VariantKind.ENCODER),
    )

    def test_the_projects_are_judged_together_and_the_baseline_is_left_out(self) -> None:
        measurements = (
            _measurement(self.short, BASELINE, STREAM),
            _measurement(self.long, BASELINE, STREAM),
            _measurement(self.stem, BASELINE, STREAM),
            _measurement(self.short, "shrinks", STREAM),
            _measurement(self.long, "shrinks", STREAM - 60),
            _measurement(self.stem, "shrinks", STREAM - 10),
            _measurement(self.short, "projects-only", STREAM - 40),
            _measurement(self.long, "projects-only", STREAM - 40),
        )
        baseline = 2 * measurements[0].block

        rows = verdict_rows(group_rows(measurements, BASELINE), measurements, self.variants)

        assert [row.variant for row in rows] == ["shrinks", "projects-only"]
        assert rows[0].projects == pytest.approx(-60 / baseline)
        assert rows[0].reconstructions == pytest.approx(-10 / measurements[2].block)
        assert rows[0].worst == pytest.approx(0.0)
        assert rows[0].verdict is Verdict.PROVISIONAL
        assert rows[1].reconstructions is None
        assert rows[1].cells[4] == ""

    def test_a_variant_the_run_left_out_takes_no_row(self) -> None:
        measurements = (_measurement(self.short, BASELINE, STREAM), _measurement(self.short, "shrinks", STREAM))

        rows = verdict_rows(group_rows(measurements, BASELINE), measurements, self.variants)

        assert [row.variant for row in rows] == ["shrinks"]
        assert rows[0].verdict is Verdict.REJECTED

    def test_a_written_encoding_graduates_outright(self) -> None:
        written = replace(self.variants[2], kind=VariantKind.ENCODER)
        measurements = (
            _measurement(self.short, BASELINE, STREAM),
            _measurement(self.short, written.name, STREAM - 50),
        )

        rows = verdict_rows(group_rows(measurements, BASELINE), measurements, (self.variants[0], written))

        assert rows[0].verdict is Verdict.PROVISIONAL
