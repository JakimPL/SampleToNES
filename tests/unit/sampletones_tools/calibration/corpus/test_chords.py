from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.config.chords import ChordsConfig
from sampletones_tools.calibration.corpus.chords import build_chords

TONE: Final[Dict[str, Any]] = {"on": True, "pitch": 69, "volume": 12, "duty_cycle": 2}
BASS: Final[Dict[str, Any]] = {"on": True, "pitch": 45}


def _corpus(frames: Dict[str, Dict[str, Any]]) -> ChordsConfig:
    return ChordsConfig.model_validate(
        {
            "sounding_frames": 3,
            "silent_frames": 1,
            "chords": [{"name": "chord", "category": "chords-two", "listed": True, "frames": frames}],
        }
    )


class TestBuildChords:
    def test_every_channel_holds_its_frame_together_then_falls_silent(self) -> None:
        (chord,) = build_chords(Config(), corpus=_corpus({"pulse1": TONE, "triangle": BASS}))

        assert chord.truth is not None
        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            assert [frame.on for frame in chord.truth.instructions[channel]] == [True, True, True, False]

    def test_a_frame_its_channel_cannot_play_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            build_chords(Config(), corpus=_corpus({"pulse1": TONE, "noise": BASS}))
