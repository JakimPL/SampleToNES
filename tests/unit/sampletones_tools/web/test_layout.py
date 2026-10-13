import re
from pathlib import Path
from typing import Final, Set

import pytest

from sampletones_tools.web.design import ApplicationDesign
from sampletones_tools.web.paths import STATIC_DIRECTORY
from sampletones_tools.web.writer import FONTS_STYLESHEET, LAYOUT_STYLESHEETS, MARK_FILE, ROLES_STYLESHEET, write_layout

COLOR_LITERAL: Final[re.Pattern[str]] = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
USED: Final[re.Pattern[str]] = re.compile(r"var\(--([a-z0-9-]+)\)")
DECLARED: Final[re.Pattern[str]] = re.compile(r"--([a-z0-9-]+):")
URL: Final[re.Pattern[str]] = re.compile(r'url\("?([^")]+)')


@pytest.fixture(scope="module")
def written(tmp_path_factory: pytest.TempPathFactory, design: ApplicationDesign) -> Path:
    directory = tmp_path_factory.mktemp("layout")
    write_layout(directory, design)
    return directory


def declared_names(directory: Path) -> Set[str]:
    names: Set[str] = set()
    for stylesheet in directory.glob("*.css"):
        names.update(DECLARED.findall(stylesheet.read_text(encoding="utf-8")))
    return names


class TestStaticStylesheets:
    @pytest.mark.parametrize("name", LAYOUT_STYLESHEETS)
    def test_no_color_is_written_into_a_shared_stylesheet(self, name: str) -> None:
        assert COLOR_LITERAL.findall((STATIC_DIRECTORY / name).read_text(encoding="utf-8")) == []

    @pytest.mark.parametrize("name", LAYOUT_STYLESHEETS)
    def test_every_variable_a_stylesheet_reads_is_declared(self, name: str, written: Path) -> None:
        used = set(USED.findall((STATIC_DIRECTORY / name).read_text(encoding="utf-8")))

        assert sorted(used - declared_names(written)) == []


class TestWriteLayout:
    def test_returns_the_stylesheets_in_link_order(self, tmp_path: Path, design: ApplicationDesign) -> None:
        assert write_layout(tmp_path, design) == (FONTS_STYLESHEET, ROLES_STYLESHEET, *LAYOUT_STYLESHEETS)

    def test_every_file_lands_beside_the_mark(self, written: Path) -> None:
        for name in (FONTS_STYLESHEET, ROLES_STYLESHEET, *LAYOUT_STYLESHEETS, MARK_FILE):
            assert (written / name).is_file()

    def test_the_faces_travel_inside_the_stylesheet(self, written: Path) -> None:
        urls = URL.findall((written / FONTS_STYLESHEET).read_text(encoding="utf-8"))

        assert urls
        assert [url for url in urls if not url.startswith("data:")] == []

    def test_the_roles_carry_the_ground_of_the_design(self, written: Path, design: ApplicationDesign) -> None:
        roles = (written / ROLES_STYLESHEET).read_text(encoding="utf-8")

        assert "--ground: #" in roles
        assert "--size-sans-medium:" in roles
        assert "--font-icon:" in roles

    def test_the_output_is_the_same_on_every_write(self, tmp_path: Path, design: ApplicationDesign) -> None:
        first, second = tmp_path / "first", tmp_path / "second"
        write_layout(first, design)
        write_layout(second, design)

        for path in first.iterdir():
            assert path.read_bytes() == (second / path.name).read_bytes()
