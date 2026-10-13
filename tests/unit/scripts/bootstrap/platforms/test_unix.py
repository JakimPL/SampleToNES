from pathlib import Path

import pytest

from bootstrap.platforms.unix import unix_site_packages


class TestUnixSitePackages:
    def test_the_one_versioned_directory_is_found(self, tmp_path: Path) -> None:
        site_packages = tmp_path / "lib" / "python3.12" / "site-packages"
        site_packages.mkdir(parents=True)
        (tmp_path / "lib" / "python3.12" / "config").mkdir()

        assert unix_site_packages(tmp_path) == site_packages

    def test_an_environment_without_one_is_refused(self, tmp_path: Path) -> None:
        (tmp_path / "lib").mkdir()

        with pytest.raises(FileNotFoundError, match="found 0"):
            unix_site_packages(tmp_path)

    def test_an_environment_holding_two_is_refused(self, tmp_path: Path) -> None:
        for version in ("python3.12", "python3.13"):
            (tmp_path / "lib" / version / "site-packages").mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="found 2"):
            unix_site_packages(tmp_path)
