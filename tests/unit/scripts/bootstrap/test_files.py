from pathlib import Path

from bootstrap.files import remove_path


class TestRemovePath:
    def test_a_directory_goes_with_everything_under_it(self, tmp_path: Path) -> None:
        directory = tmp_path / "bin"
        (directory / "nested").mkdir(parents=True)
        (directory / "nested" / "file").write_text("")

        assert remove_path(directory)
        assert not directory.exists()

    def test_a_file_goes(self, tmp_path: Path) -> None:
        file = tmp_path / "sampletones.spec"
        file.write_text("")

        assert remove_path(file)
        assert not file.exists()

    def test_an_absent_path_is_reported_as_nothing_removed(self, tmp_path: Path) -> None:
        assert not remove_path(tmp_path / "absent")
