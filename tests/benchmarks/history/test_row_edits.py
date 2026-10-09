import copy
from itertools import count
from typing import Final

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_shared.constants.general import BYTES_PER_MEGABYTE
from tests.suite.memory import retained_bytes
from tests.suite.timing import seconds

SONG_PATTERNS: Final[int] = 300
ROWS_PER_PATTERN: Final[int] = 64
VOLUMES: Final[int] = 16
EDITS: Final[int] = 20
ENTRY_SHARE: Final[float] = 0.01
LANDING_SHARE: Final[float] = 0.1
EDITED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


def _written_pattern(frame: int) -> Pattern:
    rows = {row: Row(volume=(row + frame) % VOLUMES) for row in range(ROWS_PER_PATTERN)}
    return Pattern.empty(ROWS_PER_PATTERN).with_rows(rows)


@pytest.fixture(name="arranged")
def arranged_fixture(controller: ProjectController) -> ProjectController:
    """A written song of SONG_PATTERNS patterns, each frame a pattern of its own on every channel."""
    song = controller.project.song
    song.resize_patterns(ROWS_PER_PATTERN)
    frames = SONG_PATTERNS // len(song.channels)
    for frame in range(frames):
        if frame >= song.order_length():
            song.append_frame()
        for channel_name, channel in song.channels.items():
            channel.patterns[frame] = _written_pattern(frame)
            song.set_order_entry(frame, channel_name, frame)

    return controller


def _land(
    controller: ProjectController,
    history: HistoryManager,
    step: int,
) -> None:
    """Writes a volume into one cell, a cell of its own for each step, each write changing the cell it reaches."""
    song = controller.project.song
    pattern_index = step % song.order_length()
    row_index = step % ROWS_PER_PATTERN
    held = song.channels[EDITED_CHANNEL].get_row(pattern_index, row_index)
    volume = ((held.volume or 0) + 1) % VOLUMES
    with history.transaction(HistoryAction.EDIT_ROW):
        controller.set_row(EDITED_CHANNEL, pattern_index, row_index, volume=volume)


class TestARowEditHoldsOnePattern:
    """An entry a row edit leaves holds the one pattern the edit wrote, and shares every other pattern
    and every row with the entries beside it.

    The reference is what copying the song leaves allocated, which is what an entry held while a
    snapshot copied every row. An entry holds a sliver of it: the pattern it wrote, and the order and
    the pattern pools around the patterns.
    """

    def test_an_entry_holds_a_sliver_of_the_song(
        self,
        arranged: ProjectController,
        history: HistoryManager,
    ) -> None:
        song = arranged.project.song
        steps = count(1)
        whole = retained_bytes(lambda: copy.deepcopy(song))

        def edits() -> None:
            for _ in range(EDITS):
                _land(arranged, history, next(steps))

        per_entry = retained_bytes(edits) / EDITS

        assert (
            per_entry < whole * ENTRY_SHARE
        ), f"an entry {per_entry / BYTES_PER_MEGABYTE:.3f} MB, the song {whole / BYTES_PER_MEGABYTE:.2f} MB"


class TestARowEditLandsAtOnePatternsCost:
    """Landing a row edit writes one pattern and copies the order and the pools around the patterns.

    The reference is copying the song, which is what landing paid while a snapshot copied every row.
    """

    def test_landing_costs_a_sliver_of_a_copy(
        self,
        arranged: ProjectController,
        history: HistoryManager,
    ) -> None:
        song = arranged.project.song
        steps = count(1)

        copying = seconds(lambda: copy.deepcopy(song))
        landing = seconds(lambda: _land(arranged, history, next(steps)))

        assert landing < copying * LANDING_SHARE, f"landing {landing:.5f} s, copying the song {copying:.4f} s"
