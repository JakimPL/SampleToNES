import re
from pathlib import Path, PurePosixPath
from typing import Final, List, Set

import pytest

from sampletones_tools.calibration.board.layout import (
    DATA_FILE,
    FONTS_FILE,
    GENERATED_FILES,
    PAGE_DIRECTORY,
    PAGE_FILE,
    PALETTE_FILE,
    SHIPPED_FILES,
)
from sampletones_tools.calibration.board.palette import board_palette, palette_names, palette_stylesheet
from sampletones_tools.calibration.board.paths import STATIC_DIRECTORY
from sampletones_tools.calibration.board.session import BoardRequest, build_board

MARKUP_REFERENCE: Final[re.Pattern[str]] = re.compile(r'(?:src|href)="([^"]+)"')
CLIP_REFERENCE: Final[re.Pattern[str]] = re.compile(r'"((?:[\w.+-]+/)+[\w.+-]+\.flac)"')
STYLE_REFERENCE: Final[re.Pattern[str]] = re.compile(r'url\("(?!data:)([^"]+)"\)')


def referenced(page: Path) -> Set[str]:
    """Every file the written page asks for, by the reference the page spells."""
    references = set(MARKUP_REFERENCE.findall(page.read_text(encoding="utf-8")))
    directory = page.parent / PAGE_DIRECTORY
    data = (directory / DATA_FILE).read_text(encoding="utf-8")
    references.update(CLIP_REFERENCE.findall(data))
    for name in (PALETTE_FILE, FONTS_FILE):
        references.update(
            f"{PAGE_DIRECTORY}/{reference}"
            for reference in STYLE_REFERENCE.findall((directory / name).read_text(encoding="utf-8"))
        )

    return references


class TestBuildBoard:
    def test_a_run_gains_one_page_and_the_files_it_reads(self, run: Path) -> None:
        page = build_board(BoardRequest(runs=[run], output=run))

        assert page == run / PAGE_FILE
        assert page.is_file()
        for name in (*SHIPPED_FILES, *GENERATED_FILES):
            if name != PAGE_FILE:
                assert (run / PAGE_DIRECTORY / name).is_file()

    def test_every_reference_of_a_page_in_its_run_resolves(self, run: Path) -> None:
        page = build_board(BoardRequest(runs=[run], output=run))

        missing = [reference for reference in referenced(page) if not (run / PurePosixPath(reference)).is_file()]
        assert missing == []

    def test_every_reference_of_a_page_comparing_runs_resolves(self, runs: List[Path], tmp_path: Path) -> None:
        output = tmp_path / "comparison"

        page = build_board(BoardRequest(runs=runs, output=output))

        references = referenced(page)
        assert any(reference.endswith(".flac") for reference in references)
        missing = [reference for reference in references if not (output / PurePosixPath(reference)).is_file()]
        assert missing == []

    def test_the_shipped_files_travel_unchanged(self, run: Path) -> None:
        build_board(BoardRequest(runs=[run], output=run))

        for name in SHIPPED_FILES:
            written = run / name if name == PAGE_FILE else run / PAGE_DIRECTORY / name
            assert written.read_bytes() == (STATIC_DIRECTORY / name).read_bytes()

    @pytest.mark.parametrize("name", palette_names())
    def test_a_page_is_drawn_in_the_palette_it_is_asked_for(self, run: Path, name: str) -> None:
        build_board(BoardRequest(runs=[run], output=run, palette=name))

        stylesheet = (run / PAGE_DIRECTORY / PALETTE_FILE).read_text(encoding="utf-8")
        assert stylesheet == palette_stylesheet(board_palette(name))

    def test_an_unknown_palette_is_refused(self, run: Path) -> None:
        with pytest.raises(KeyError):
            build_board(BoardRequest(runs=[run], output=run, palette="sunset"))

    def test_a_page_without_a_run_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            BoardRequest(runs=[], output=tmp_path)
