from pathlib import Path

import pytest

from sampletones_tools.codec.study.manifest import StudyManifest, StudySource
from sampletones_tools.codec.study.session import resolve_manifest, variant_names
from sampletones_tools.codec.study.variants.registry import EVERY_VARIANT


class TestVariantNames:
    def test_nothing_named_is_every_variant(self) -> None:
        assert variant_names(None) == (EVERY_VARIANT,)

    def test_names_are_read_in_order_with_their_spaces_stripped(self) -> None:
        assert variant_names("wide-hold, default-count") == ("wide-hold", "default-count")


class TestResolveManifest:
    def test_sources_named_outright_are_measured(self) -> None:
        manifest = resolve_manifest(
            None,
            projects=(Path("songs/one.stp"),),
            reconstructions=(Path("stems/two"),),
            lengthen_seconds=30,
            variants=("wide-hold",),
        )

        assert manifest.projects == (StudySource(label="one", path=Path("songs/one.stp")),)
        assert manifest.reconstructions == (StudySource(label="two", path=Path("stems/two")),)
        assert manifest.lengthen_seconds == 30
        assert manifest.variants == ("wide-hold",)

    def test_a_run_naming_no_source_and_no_manifest_is_refused(self) -> None:
        with pytest.raises(ValueError, match="reads the files it is given"):
            resolve_manifest(
                None,
                projects=(),
                reconstructions=(),
                lengthen_seconds=30,
                variants=(EVERY_VARIANT,),
            )

    def test_a_manifest_missing_from_its_path_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No manifest at"):
            resolve_manifest(
                tmp_path / "absent.json",
                projects=(),
                reconstructions=(),
                lengthen_seconds=30,
                variants=(EVERY_VARIANT,),
            )

    def test_a_manifest_file_is_measured_as_it_stands(self, tmp_path: Path) -> None:
        written = StudyManifest(
            projects=(StudySource(label="one", path=Path("songs/one.stp")),),
            reconstructions=(),
            lengthen_seconds=45,
            variants=("wide-hold",),
        )
        path = tmp_path / "manifest.json"
        written.save(path)

        manifest = resolve_manifest(
            path,
            projects=(),
            reconstructions=(),
            lengthen_seconds=30,
            variants=(EVERY_VARIANT,),
        )

        assert manifest == written

    def test_sources_named_outright_replace_a_manifest_s_own_and_keep_its_sweep(self, tmp_path: Path) -> None:
        path = tmp_path / "manifest.json"
        StudyManifest(
            projects=(StudySource(label="one", path=Path("songs/one.stp")),),
            reconstructions=(),
            lengthen_seconds=45,
            variants=("wide-hold",),
        ).save(path)

        manifest = resolve_manifest(
            path,
            projects=(),
            reconstructions=(Path("stems/two"),),
            lengthen_seconds=30,
            variants=(EVERY_VARIANT,),
        )

        assert manifest.projects == ()
        assert manifest.reconstructions == (StudySource(label="two", path=Path("stems/two")),)
        assert (manifest.lengthen_seconds, manifest.variants) == (45, ("wide-hold",))


class TestStudyManifest:
    def test_a_manifest_naming_no_source_is_refused(self) -> None:
        with pytest.raises(ValueError, match="reads the files it is given"):
            StudyManifest(projects=(), reconstructions=(), lengthen_seconds=45, variants=("wide-hold",))
