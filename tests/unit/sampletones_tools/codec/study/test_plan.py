from pathlib import Path
from typing import Tuple

import pytest

from sampletones_tools.codec.study.manifest import StudyManifest, StudySource
from sampletones_tools.codec.study.plan import plan_study
from sampletones_tools.codec.study.variants.production import BASELINE_NAME
from tests.suite.files import empty_file


def _manifest(directory: Path, variants: Tuple[str, ...]) -> StudyManifest:
    return StudyManifest(
        projects=(StudySource.at(empty_file(directory, "one.stp")),),
        reconstructions=(),
        lengthen_seconds=45,
        variants=variants,
    )


class TestPlanStudy:
    def test_the_variants_are_the_ones_the_manifest_names_after_the_baseline(self, tmp_path: Path) -> None:
        manifest = _manifest(tmp_path, ("wide-hold",))

        plan = plan_study(manifest)

        assert plan.manifest == manifest
        assert [variant.name for variant in plan.variants] == [BASELINE_NAME, "wide-hold"]

    def test_an_unknown_variant_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No variant is called bogus"):
            plan_study(_manifest(tmp_path, ("bogus",)))
