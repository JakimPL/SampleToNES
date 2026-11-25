from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_tools.calibration.config.chords import ChordConfig, ChordsConfig

CHORD: Final[Dict[str, Any]] = {
    "name": "chord",
    "category": "chords-two",
    "listed": True,
    "frames": {
        "pulse1": {"on": True, "pitch": 69, "volume": 12, "duty_cycle": 2},
        "triangle": {"on": True, "pitch": 45},
    },
}


class TestChordConfig:
    def test_a_chord_of_one_channel_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ChordConfig.model_validate({**CHORD, "frames": {"triangle": {"on": True, "pitch": 45}}})


class TestChordsConfig:
    def test_two_chords_of_one_name_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="name of its own"):
            ChordsConfig.model_validate({"sounding_frames": 3, "silent_frames": 1, "chords": [CHORD, CHORD]})

    def test_the_packaged_chords_read(self) -> None:
        assert ChordsConfig.load().chords
