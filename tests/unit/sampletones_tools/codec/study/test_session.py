from pathlib import Path

from sampletones_tools.codec.study.manifest import StudyManifest, StudySource
from sampletones_tools.codec.study.session import resolve_manifest, variant_names
from sampletones_tools.codec.study.variants.registry import EVERY_VARIANT


class TestVariantNames:
    def test_nothing_named_is_every_variant(self) -> None:
        assert variant_names(None) == (EVERY_VARIANT,)

    def test_names_are_read_in_order_with_their_spaces_stripped(self) -> None:
        assert variant_names("wide-hold, default-count") == ("wide-hold", "default-count")


class TestResolveManifest:
    def test_sources_named_outright_stand_in_for_the_corpus(self) -> None:
        manifest = resolve_manifest(
            None,
            projects=(Path("songs/one.stp"),),
            reconstructions=(Path("stems/two"),),
            lengthen_seconds=30,
            variants=("wide-hold",),
            quick=False,
        )

        assert manifest.projects == (StudySource(label="one", path=Path("songs/one.stp")),)
        assert manifest.reconstructions == (StudySource(label="two", path=Path("stems/two")),)
        assert manifest.lengthen_seconds == 30
        assert manifest.variants == ("wide-hold",)

    def test_without_sources_the_corpus_on_this_machine_is_read(self) -> None:
        manifest = resolve_manifest(
            None,
            projects=(),
            reconstructions=(),
            lengthen_seconds=30,
            variants=(EVERY_VARIANT,),
            quick=True,
        )

        assert manifest == StudyManifest.default(lengthen_seconds=30, variants=(EVERY_VARIANT,), quick=True)
        assert manifest.projects
