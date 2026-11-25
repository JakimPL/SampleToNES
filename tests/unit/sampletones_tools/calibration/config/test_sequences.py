from typing import Any, Dict, Final, List

import pytest
from pydantic import ValidationError

from sampletones_tools.calibration.config.sequences import SequenceConfig, SequencesConfig

TONE: Final[Dict[str, Any]] = {"on": True, "pitch": 60, "volume": 15, "duty_cycle": 2}
BASS: Final[Dict[str, Any]] = {"on": True, "pitch": 48}


def _item(name: str, pulse_frames: int, triangle_frames: int) -> Dict[str, Any]:
    return {
        "name": name,
        "category": "sequences-mixed",
        "channels": {
            "pulse1": [{"count": pulse_frames, "frame": TONE}],
            "triangle": [{"count": triangle_frames, "frame": BASS}],
        },
    }


class TestSequenceConfig:
    def test_channels_lasting_alike_are_read(self) -> None:
        item = SequenceConfig.model_validate(_item("tune", 4, 4))

        assert [run.count for runs in item.channels.values() for run in runs] == [4, 4]

    def test_channels_lasting_differently_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="as many frames"):
            SequenceConfig.model_validate(_item("tune", 4, 3))


class TestSequencesConfig:
    def test_two_sounds_of_one_name_are_refused(self) -> None:
        items: List[Dict[str, Any]] = [_item("tune", 2, 2), _item("tune", 3, 3)]

        with pytest.raises(ValidationError, match="name of its own"):
            SequencesConfig.model_validate({"items": items})

    def test_the_packaged_corpus_reads(self) -> None:
        assert SequencesConfig.load().items
