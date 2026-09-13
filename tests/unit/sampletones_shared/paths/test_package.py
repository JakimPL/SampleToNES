from pathlib import Path

import pytest

import sampletones_config
from sampletones_shared.paths.package import package_directory


class TestPackageDirectory:
    def test_the_directory_holds_the_package_s_modules_and_data(self) -> None:
        directory = package_directory("sampletones_config")

        assert directory == Path(sampletones_config.__file__).parent
        assert (directory / "application").is_dir()

    def test_a_nested_package_is_placed_by_its_own_location(self) -> None:
        assert package_directory("sampletones_tools.corpus.config").name == "config"

    def test_a_directory_of_data_alone_is_placed_as_a_namespace_package(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A bundle unpacks a package the application never imports as code this way."""
        (tmp_path / "unpacked_data").mkdir()
        (tmp_path / "unpacked_data" / "values.yaml").write_text("")
        monkeypatch.syspath_prepend(str(tmp_path))

        assert package_directory("unpacked_data") == tmp_path / "unpacked_data"

    def test_an_absent_package_is_refused(self) -> None:
        with pytest.raises(FileNotFoundError, match="sampletones_absent"):
            package_directory("sampletones_absent")
