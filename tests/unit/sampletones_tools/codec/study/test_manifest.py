from pathlib import Path

import pytest

from sampletones_tools.codec.study.manifest import NAMES_A_SOURCE, StudyManifest, StudySource
from tests.suite.files import empty_file


class TestStudySource:
    def test_a_file_is_labeled_by_its_stem_and_a_directory_by_its_name(self, tmp_path: Path) -> None:
        project = empty_file(tmp_path, "one.stp")

        assert StudySource.at(project) == StudySource(label="one", path=project)
        assert StudySource.at(tmp_path) == StudySource(label=tmp_path.name, path=tmp_path)

    def test_a_source_naming_nothing_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No file at"):
            StudySource.at(tmp_path / "absent.stp")


class TestStudyManifest:
    def test_a_manifest_naming_no_source_is_refused(self) -> None:
        with pytest.raises(ValueError, match=NAMES_A_SOURCE):
            StudyManifest(projects=(), reconstructions=(), lengthen_seconds=45, variants=("wide-hold",))

    def test_a_saved_manifest_loads_as_it_was_written(self, tmp_path: Path) -> None:
        written = StudyManifest(
            projects=(StudySource.at(empty_file(tmp_path, "one.stp")),),
            reconstructions=(StudySource.at(tmp_path),),
            lengthen_seconds=45,
            variants=("wide-hold",),
        )
        path = tmp_path / "manifest.json"
        written.save(path)

        assert StudyManifest.load(path) == written
