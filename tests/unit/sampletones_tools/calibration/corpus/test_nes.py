from typing import Final

import numpy as np
import pytest

from sampletones_core.audio.mixing import mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import render_channels
from sampletones_tools.calibration.config.nes import NesCorpusConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.nes import build_nes_corpus

FRAMES: Final[int] = 6
CORPUS: Final[NesCorpusConfig] = NesCorpusConfig.model_validate(
    {
        "items": [
            {
                "name": "tune",
                "category": "nes-mix",
                "channels": {
                    "pulse1": [
                        {"count": 4, "frame": {"on": True, "pitch": 60, "volume": 15, "duty_cycle": 2}},
                        {"count": 2, "frame": {"on": False, "pitch": 60, "volume": 0, "duty_cycle": 2}},
                    ],
                    "noise": [{"count": FRAMES, "frame": {"on": True, "period": 3, "volume": 9, "short": False}}],
                },
            }
        ]
    }
)


@pytest.fixture(name="item", scope="module")
def item_fixture() -> CorpusItem:
    (item,) = build_nes_corpus(Config(), corpus=CORPUS)
    return item


class TestBuildNesCorpus:
    def test_the_sound_is_what_its_channels_render(self, item: CorpusItem) -> None:
        assert item.truth is not None
        expected = mix(list(render_channels(item.truth.instructions, Config()).values()))

        np.testing.assert_allclose(item.audio, expected, atol=1e-6)
        assert item.audio.shape == (FRAMES * Config().library.frame_length,)

    def test_the_truth_holds_the_frames_written(self, item: CorpusItem) -> None:
        assert item.truth is not None
        pulse = item.truth.instructions[ChannelName.PULSE1]

        assert [instruction.on for instruction in pulse] == [True] * 4 + [False] * 2
        assert len(item.truth.instructions[ChannelName.NOISE]) == FRAMES

    def test_the_tonal_lines_sound_where_their_frames_do(self, item: CorpusItem) -> None:
        assert item.truth is not None
        line = item.truth.pitches[ChannelName.PULSE1.value]

        assert [pitch is not None for pitch in line] == [True] * 4 + [False] * 2
        assert ChannelName.NOISE.value not in item.truth.pitches

    def test_a_round_trip_covers_every_channel(self, item: CorpusItem) -> None:
        assert item.channels == frozenset(ChannelName.items())
