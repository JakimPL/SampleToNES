from pathlib import Path
from typing import Final

import pytest

from assets.footage.schedule import Run, Schedule
from assets.footage.shoot import MissingTakeError, Shoot, Take, handed_take, take_environment
from assets.footage.specification import Listening
from sampletones_core.constants.enums import AudioSourceType

TAKE: Final[Take] = Take(
    shoot=Shoot(
        document=Path("/captures/final.stn"),
        digest="0" * 64,
        tick_length=735,
        stem_keys={"Vocals": "0", "Drums": "1"},
        schedule=Schedule(
            first_tick=68,
            ticks_per_frame=1,
            frame_count=120,
            runs=(
                Run(listening=Listening(AudioSourceType.ORIGINAL, ("Drums", "Vocals")), first=0, last=60),
                Run(listening=Listening(AudioSourceType.RECONSTRUCTION, ("Vocals",)), first=60, last=120),
            ),
        ),
    ),
    frames=Path("/build/footage/reel/frames"),
    stop=120,
)


class TestHandedTake:
    def test_the_take_reaches_the_scene_whole(self) -> None:
        assert handed_take(take_environment(TAKE)) == TAKE

    def test_a_scene_run_with_no_take_is_refused(self) -> None:
        with pytest.raises(MissingTakeError):
            handed_take({})
