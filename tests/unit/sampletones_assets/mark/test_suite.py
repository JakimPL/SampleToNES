from pathlib import Path

import pytest
from PIL import Image

from sampletones_assets.mark.specification import Mark
from sampletones_assets.mark.suite import write_icon_suite
from sampletones_shared.paths.resources import (
    ICON_UNIX_FILENAME,
    ICON_VECTOR_FILENAME,
    ICON_WIN_FILENAME,
)

RGBA_MODE = "RGBA"
ICO_SIZES_KEY = "sizes"


@pytest.fixture(name="mark", scope="module")
def mark_fixture() -> Mark:
    return Mark.load()


class TestWriteIconSuite:
    def test_the_suite_holds_every_file_the_application_ships(self, tmp_path: Path, mark: Mark) -> None:
        paths = write_icon_suite(tmp_path, mark)
        assert [path.name for path in paths] == [
            ICON_VECTOR_FILENAME,
            ICON_UNIX_FILENAME,
            ICON_WIN_FILENAME,
        ]
        assert all(path.is_file() for path in paths)

    def test_the_directory_is_created_where_it_is_missing(self, tmp_path: Path, mark: Mark) -> None:
        directory = tmp_path / "icons"
        write_icon_suite(directory, mark)
        assert directory.is_dir()

    def test_the_raster_is_the_size_the_definition_declares(self, tmp_path: Path, mark: Mark) -> None:
        write_icon_suite(tmp_path, mark)
        with Image.open(tmp_path / ICON_UNIX_FILENAME) as image:
            assert image.size == (mark.render.raster_size, mark.render.raster_size)
            assert image.mode == RGBA_MODE

    def test_the_windows_icon_carries_every_declared_size(self, tmp_path: Path, mark: Mark) -> None:
        write_icon_suite(tmp_path, mark)
        with Image.open(tmp_path / ICON_WIN_FILENAME) as image:
            carried = {width for width, _ in image.info[ICO_SIZES_KEY]}

        assert carried == set(mark.render.windows_sizes)

    def test_the_same_definition_writes_the_same_files(self, tmp_path: Path, mark: Mark) -> None:
        """One definition produces one suite, so a rebuild leaves the shipped files as they were."""
        first = write_icon_suite(tmp_path / "first", mark)
        second = write_icon_suite(tmp_path / "second", mark)
        assert [path.read_bytes() for path in first] == [path.read_bytes() for path in second]
