from typing import Final

import numpy as np
import pytest

from sampletones_core.audio.mixing import mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import render_channels
from sampletones_core.instructions import PulseInstruction
from sampletones_tools.calibration.config.sequences import SequencesConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.nes import build_sequences, held

FRAMES: Final[int] = 6
CORPUS: Final[SequencesConfig] = SequencesConfig.model_validate(
    {
        "items": [
            {
                "name": "tune",
                "category": "sequences-mixed",
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
    (item,) = build_sequences(Config(), corpus=CORPUS)
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


class TestHeld:
    def test_an_instruction_holds_then_the_channel_falls_silent(self) -> None:
        tone = PulseInstruction(on=True, pitch=60, volume=9, duty_cycle=1)

        frames = held(ChannelName.PULSE1, tone, sounding=3, silent=2)

        assert frames[:3] == [tone] * 3
        assert [frame.on for frame in frames[3:]] == [False, False]
