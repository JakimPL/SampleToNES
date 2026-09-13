import zipfile
from pathlib import Path
from typing import List

import pytest

from bootstrap.layout import BUNDLES, DISTRIBUTION
from bootstrap.project import read_project
from tests.suite.bootstrap import PROJECT_NAME, PROJECT_VERSION, write_project
from tests.suite.scripts import load_script

archive_bundle = load_script("archive_bundle.py")

LABEL = "windows-x86_64"
ROOT = f"{PROJECT_NAME}-v{PROJECT_VERSION}-{LABEL}"

LAUNCHER = "sampletones.exe"
LIBRARY = "_internal/python312.dll"
NOTICES = "THIRD-PARTY-NOTICES.md"


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    source = tmp_path / "bin" / "sampletones"
    (source / "_internal" / "empty").mkdir(parents=True)
    (source / LAUNCHER).write_bytes(b"MZ")
    (source / LIBRARY).write_bytes(b"library")
    (source / NOTICES).write_text("notices")
    return source


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    return tmp_path / "bundles" / f"{ROOT}.zip"


def _names(archive: Path) -> List[str]:
    with zipfile.ZipFile(archive) as bundle:
        return bundle.namelist()


class TestWriteArchive:
    def test_every_entry_sits_under_the_root_directory(self, bundle: Path, archive: Path) -> None:
        archive_bundle.write_archive(bundle, archive, root=ROOT)

        names = _names(archive)
        assert names
        assert all(name.startswith(f"{ROOT}/") for name in names)

    def test_bundle_contents_are_archived(self, bundle: Path, archive: Path) -> None:
        archive_bundle.write_archive(bundle, archive, root=ROOT)

        names = _names(archive)
        assert f"{ROOT}/{LAUNCHER}" in names
        assert f"{ROOT}/{LIBRARY}" in names
        assert f"{ROOT}/{NOTICES}" in names

    def test_empty_directories_are_kept(self, bundle: Path, archive: Path) -> None:
        archive_bundle.write_archive(bundle, archive, root=ROOT)

        assert f"{ROOT}/_internal/empty/" in _names(archive)

    def test_file_contents_survive_the_round_trip(self, bundle: Path, archive: Path) -> None:
        archive_bundle.write_archive(bundle, archive, root=ROOT)

        with zipfile.ZipFile(archive) as written:
            assert written.read(f"{ROOT}/{LIBRARY}") == b"library"

    def test_missing_target_directory_is_created(self, bundle: Path, archive: Path) -> None:
        archive_bundle.write_archive(bundle, archive, root=ROOT)

        assert archive.is_file()

    def test_repeated_runs_archive_the_same_order(self, bundle: Path, tmp_path: Path) -> None:
        first = tmp_path / "first.zip"
        second = tmp_path / "second.zip"

        archive_bundle.write_archive(bundle, first, root=ROOT)
        archive_bundle.write_archive(bundle, second, root=ROOT)

        assert _names(first) == _names(second)

    def test_source_directory_is_left_in_place(self, bundle: Path, archive: Path) -> None:
        """Archiving reads the bundle where it lies, so the build output keeps its own name."""
        archive_bundle.write_archive(bundle, archive, root=ROOT)

        assert bundle.is_dir()
        assert (bundle / LAUNCHER).is_file()

    def test_archives_while_a_handle_is_held_inside_the_bundle(self, bundle: Path, archive: Path) -> None:
        """A process that ran the executable, or a virus scanner reading it, leaves the archive reachable.

        Windows refuses to rename a directory holding an open file, which is the condition this
        reproduces; reading each entry in place keeps the bundle archivable throughout.
        """

        with (bundle / LIBRARY).open("rb"):
            archive_bundle.write_archive(bundle, archive, root=ROOT)

        assert f"{ROOT}/{LIBRARY}" in _names(archive)


class TestArchiveRoot:
    def test_the_root_names_the_project_its_version_and_the_platform(self, tmp_path: Path) -> None:
        assert archive_bundle.archive_root(read_project(write_project(tmp_path)), LABEL) == ROOT


class TestMain:
    def test_the_release_bundle_is_archived_into_the_bundles_directory(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        root = write_project(tmp_path / "repository")
        source = root / DISTRIBUTION / PROJECT_NAME
        source.mkdir(parents=True)
        (source / LAUNCHER).write_bytes(b"MZ")
        monkeypatch.setattr(archive_bundle, "repository_root", lambda: root)

        assert archive_bundle.main(["--label", LABEL]) == 0
        assert _names(root / BUNDLES / f"{ROOT}.zip") == [f"{ROOT}/{LAUNCHER}"]

    def test_a_missing_bundle_is_annotated_and_writes_no_archive(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        root = write_project(tmp_path)
        monkeypatch.setattr(archive_bundle, "repository_root", lambda: root)

        assert archive_bundle.main(["--label", LABEL]) == 1
        assert "::error::" in capsys.readouterr().out
        assert not (root / BUNDLES).exists()
