import struct
from pathlib import Path

import pytest

from sampletones_player.specification.clock import FIXED_POINT_SCALE, NTSC_FRAME_RATE
from sampletones_player.specification.nsf import HEADER_SIZE
from sampletones_player.specification.song import (
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    TOTAL_TICKS_OFFSET,
)
from sampletones_tools.samples import render
from sampletones_tools.samples.render import RenderingError, render_directory, song_seconds

CODE_LENGTH = 10


def _exported(ticks: int, whole: int, fraction: int) -> bytes:
    block = bytearray(max(TOTAL_TICKS_OFFSET, STEP_FRACTION_OFFSET, STEP_WHOLE_OFFSET) + 2)
    struct.pack_into("<H", block, TOTAL_TICKS_OFFSET, ticks)
    block[STEP_WHOLE_OFFSET] = whole
    struct.pack_into("<H", block, STEP_FRACTION_OFFSET, fraction)
    return bytes(HEADER_SIZE + CODE_LENGTH) + bytes(block)


class TestSongSeconds:
    def test_the_length_is_the_play_calls_over_the_frame_rate(self) -> None:
        data = _exported(ticks=600, whole=1, fraction=0)

        assert song_seconds(data, CODE_LENGTH) == pytest.approx(600 / float(NTSC_FRAME_RATE))

    def test_a_fractional_step_takes_fewer_calls(self) -> None:
        data = _exported(ticks=600, whole=1, fraction=FIXED_POINT_SCALE // 2)

        assert song_seconds(data, CODE_LENGTH) == pytest.approx(400 / float(NTSC_FRAME_RATE))


class TestRenderDirectory:
    def test_a_directory_without_exports_is_refused(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(render, "require_renderer", lambda: None)

        with pytest.raises(RenderingError, match="no .nsf files"):
            render_directory(tmp_path, 0.5)
