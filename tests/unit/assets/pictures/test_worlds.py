from pathlib import Path

import pytest

from assets.demo.paths import LIBRARY_FOLDER, PROJECTS_FOLDER, RECONSTRUCTIONS_FOLDER, RECORDINGS_FOLDER
from assets.pictures.worlds import DemoTree, MissingDemoError


def demo_tree(source: Path) -> None:
    for folder in (RECORDINGS_FOLDER, LIBRARY_FOLDER, RECONSTRUCTIONS_FOLDER, PROJECTS_FOLDER):
        (source / folder).mkdir(parents=True)
        (source / folder / "file").write_text(folder)


class TestDemoTree:
    def test_the_recordings_go_beside_the_working_directory_and_the_documents_into_the_documents_folder(
        self,
        tmp_path: Path,
    ) -> None:
        source, home, documents = tmp_path / "source", tmp_path / "home", tmp_path / "home" / "Documents" / "App"
        demo_tree(source)

        DemoTree(source=source, working_directory=home, documents=documents).write()

        assert (home / RECORDINGS_FOLDER / "file").read_text() == RECORDINGS_FOLDER
        for folder in (LIBRARY_FOLDER, RECONSTRUCTIONS_FOLDER, PROJECTS_FOLDER):
            assert (documents / folder / "file").read_text() == folder

    def test_a_missing_tree_is_named(self, tmp_path: Path) -> None:
        with pytest.raises(MissingDemoError, match="make demo"):
            DemoTree(source=tmp_path / "absent", working_directory=tmp_path, documents=tmp_path).write()
