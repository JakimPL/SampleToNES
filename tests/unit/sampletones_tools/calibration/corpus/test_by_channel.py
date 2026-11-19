from typing import Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.config.chords import ChordsConfig
from sampletones_tools.calibration.corpus.by_channel import BY_CHANNEL_SUFFIX, UnwrittenSoundError, by_channel
from sampletones_tools.calibration.corpus.chords import build_chords

from ..conversions import item_named

CHORDS: Final[ChordsConfig] = ChordsConfig.model_validate(
    {
        "sounding_frames": 4,
        "silent_frames": 1,
        "chords": [
            {
                "name": "chord",
                "category": "chords-two",
                "listed": False,
                "frames": {
                    "pulse1": {"on": True, "pitch": 69, "volume": 12, "duty_cycle": 2},
                    "triangle": {"on": True, "pitch": 45},
                },
            }
        ],
    }
)


class TestByChannel:
    def test_each_channel_becomes_a_stem_held_to_that_channel(self) -> None:
        (chord,) = build_chords(Config(), corpus=CHORDS)

        split = by_channel(chord, Config())

        assert (split.name, split.category, split.listed) == (
            f"chord{BY_CHANNEL_SUFFIX}",
            f"chords-two{BY_CHANNEL_SUFFIX}",
            False,
        )
        assert split.stems is not None
        assert [entry.settings.channels for entry in split.stems.config.entries] == [
            (ChannelName.PULSE1,),
            (ChannelName.TRIANGLE,),
        ]
        np.testing.assert_allclose(sum(split.stems.sources), split.audio, atol=1e-6)

    def test_a_sound_not_written_as_frames_is_refused(self) -> None:
        with pytest.raises(UnwrittenSoundError):
            by_channel(item_named("tone", listed=True), Config())
