import zipfile
from pathlib import Path
from typing import List

import pytest

from tests.suite.scripts import load_script

zip_bundle = load_script("ci/zip_bundle.py")

ROOT = "sampletones-v0.3.0-windows-x86_64"

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
        zip_bundle.write_archive(bundle, archive, root=ROOT)

        names = _names(archive)
        assert names
        assert all(name.startswith(f"{ROOT}/") for name in names)

    def test_bundle_contents_are_archived(self, bundle: Path, archive: Path) -> None:
        zip_bundle.write_archive(bundle, archive, root=ROOT)

        names = _names(archive)
        assert f"{ROOT}/{LAUNCHER}" in names
        assert f"{ROOT}/{LIBRARY}" in names
        assert f"{ROOT}/{NOTICES}" in names

    def test_empty_directories_are_kept(self, bundle: Path, archive: Path) -> None:
        zip_bundle.write_archive(bundle, archive, root=ROOT)

        assert f"{ROOT}/_internal/empty/" in _names(archive)

    def test_file_contents_survive_the_round_trip(self, bundle: Path, archive: Path) -> None:
        zip_bundle.write_archive(bundle, archive, root=ROOT)

        with zipfile.ZipFile(archive) as written:
            assert written.read(f"{ROOT}/{LIBRARY}") == b"library"

    def test_missing_target_directory_is_created(self, bundle: Path, archive: Path) -> None:
        zip_bundle.write_archive(bundle, archive, root=ROOT)

        assert archive.is_file()

    def test_repeated_runs_archive_the_same_order(self, bundle: Path, tmp_path: Path) -> None:
        first = tmp_path / "first.zip"
        second = tmp_path / "second.zip"

        zip_bundle.write_archive(bundle, first, root=ROOT)
        zip_bundle.write_archive(bundle, second, root=ROOT)

        assert _names(first) == _names(second)

    def test_source_directory_is_left_in_place(self, bundle: Path, archive: Path) -> None:
        """Archiving reads the bundle where it lies, so the build output keeps its own name."""
        zip_bundle.write_archive(bundle, archive, root=ROOT)

        assert bundle.is_dir()
        assert (bundle / LAUNCHER).is_file()

    def test_archives_while_a_handle_is_held_inside_the_bundle(self, bundle: Path, archive: Path) -> None:
        """A process that ran the executable, or a virus scanner reading it, leaves the archive reachable.

        Windows refuses to rename a directory holding an open file, which is the condition this
        reproduces; reading each entry in place keeps the bundle archivable throughout.
        """

        with (bundle / LIBRARY).open("rb"):
            zip_bundle.write_archive(bundle, archive, root=ROOT)

        assert f"{ROOT}/{LIBRARY}" in _names(archive)


class TestMain:
    def test_reports_success_for_a_built_bundle(self, bundle: Path, archive: Path) -> None:
        assert zip_bundle.main([str(bundle), str(archive), "--root", ROOT]) == 0
        assert archive.is_file()

    def test_reports_a_missing_bundle_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        absent = tmp_path / "bin" / "sampletones"

        assert zip_bundle.main([str(absent), str(tmp_path / "out.zip"), "--root", ROOT]) == 1
        assert "::error::" in capsys.readouterr().out

    def test_a_missing_bundle_writes_no_archive(self, tmp_path: Path) -> None:
        archive = tmp_path / "out.zip"

        zip_bundle.main([str(tmp_path / "absent"), str(archive), "--root", ROOT])

        assert not archive.exists()
