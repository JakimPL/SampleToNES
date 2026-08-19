from pathlib import Path
from typing import Final

import pytest

from sampletones_player.driver.assembler.labels import (
    INIT_SYMBOL,
    LOAD_SYMBOL,
    PLAY_SYMBOL,
    SONG_SYMBOL,
    read_addresses,
    read_labels,
)
from sampletones_player.specification.driver import INIT_ADDRESS, LOAD_ADDRESS, PLAY_ADDRESS
from sampletones_shared.exceptions import DriverBuildError
from tests.suite.base import BaseTestSuite

LABELS_NAME: Final[str] = "driver.labels"
CODE_LENGTH: Final[int] = 512
SONG_ADDRESS: Final[int] = LOAD_ADDRESS + CODE_LENGTH
LABEL_FILE: Final[str] = "\n".join(
    (
        f"al {LOAD_ADDRESS:06X} .{LOAD_SYMBOL}",
        f"al {INIT_ADDRESS:06X} .{INIT_SYMBOL}",
        f"al {PLAY_ADDRESS:06X} .{PLAY_SYMBOL}",
        f"al {SONG_ADDRESS:06X} .{SONG_SYMBOL}",
        "al 000002 .current_tick",
    )
)


def write_labels(directory: Path, text: str) -> Path:
    path = directory / LABELS_NAME
    path.write_text(text)
    return path


class TestTheLabelsALinkerReports(BaseTestSuite):
    """What a build reads back out of the label file its linker wrote."""

    def test_every_symbol_carries_its_address(self, tmp_path: Path) -> None:
        labels = read_labels(write_labels(tmp_path, LABEL_FILE))
        assert labels[INIT_SYMBOL] == INIT_ADDRESS
        assert labels[SONG_SYMBOL] == SONG_ADDRESS

    def test_a_zero_page_symbol_is_read_alongside_the_program(self, tmp_path: Path) -> None:
        assert read_labels(write_labels(tmp_path, LABEL_FILE))["current_tick"] == 2

    def test_a_line_of_another_shape_carries_no_symbol(self, tmp_path: Path) -> None:
        text = f"{LABEL_FILE}\nbuilt with ld65\n"
        assert set(read_labels(write_labels(tmp_path, text))) == set(read_labels(write_labels(tmp_path, LABEL_FILE)))

    def test_the_reported_layout_is_the_driver_s_own(self, tmp_path: Path) -> None:
        addresses = read_addresses(write_labels(tmp_path, LABEL_FILE))
        assert (addresses.load, addresses.init, addresses.play, addresses.song) == (
            LOAD_ADDRESS,
            INIT_ADDRESS,
            PLAY_ADDRESS,
            SONG_ADDRESS,
        )

    def test_a_missing_symbol_is_reported(self, tmp_path: Path) -> None:
        text = "\n".join(line for line in LABEL_FILE.splitlines() if SONG_SYMBOL not in line)
        with pytest.raises(DriverBuildError, match=SONG_SYMBOL):
            read_addresses(write_labels(tmp_path, text))
