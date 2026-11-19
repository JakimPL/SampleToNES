import struct
from pathlib import Path

import pytest

from sampletones_player.specification.clock import FIXED_POINT_SCALE, MICROSECONDS_PER_SECOND
from sampletones_player.specification.nsf import HEADER_SIZE, NTSC_PERIOD_OFFSET
from sampletones_player.specification.song import (
    SONG_HEADER_SIZE,
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    TOTAL_TICKS_OFFSET,
)
from sampletones_tools.samples import render
from sampletones_tools.samples.render import RenderingError, render_directory, song_seconds

CODE_LENGTH = 10
PERIOD_MICROSECONDS = 16667


def _exported(ticks: int, whole: int, fraction: int, period: int) -> bytes:
    header = bytearray(HEADER_SIZE + CODE_LENGTH)
    struct.pack_into("<H", header, NTSC_PERIOD_OFFSET, period)
    block = bytearray(SONG_HEADER_SIZE)
    struct.pack_into("<H", block, TOTAL_TICKS_OFFSET, ticks)
    block[STEP_WHOLE_OFFSET] = whole
    struct.pack_into("<H", block, STEP_FRACTION_OFFSET, fraction)
    return bytes(header) + bytes(block)


class TestSongSeconds:
    def test_the_length_is_the_play_calls_at_the_period_the_header_asks_for(self) -> None:
        data = _exported(ticks=600, whole=1, fraction=0, period=PERIOD_MICROSECONDS)

        assert song_seconds(data, CODE_LENGTH) == pytest.approx(600 * PERIOD_MICROSECONDS / MICROSECONDS_PER_SECOND)

    def test_a_fractional_step_takes_fewer_calls(self) -> None:
        data = _exported(ticks=600, whole=1, fraction=FIXED_POINT_SCALE // 2, period=PERIOD_MICROSECONDS)

        assert song_seconds(data, CODE_LENGTH) == pytest.approx(400 * PERIOD_MICROSECONDS / MICROSECONDS_PER_SECOND)

    def test_a_longer_period_lengthens_the_song(self) -> None:
        short = song_seconds(_exported(ticks=600, whole=1, fraction=0, period=16639), CODE_LENGTH)
        long = song_seconds(_exported(ticks=600, whole=1, fraction=0, period=16667), CODE_LENGTH)

        assert long > short


class TestRenderDirectory:
    def test_a_directory_without_exports_is_refused(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(render, "require_renderer", lambda: None)

        with pytest.raises(RenderingError, match="no .nsf files"):
            render_directory(tmp_path, 0.5)
