from typing import Final

import pytest

from sampletones_application.logic.export.nsf.source.sample import SampleSource
from sampletones_application.view_model.shared.nsf.offer import FIRST_FRAME
from tests.suite.player import player_sample

SAMPLE_NAME: Final[str] = "Amen"
NTSC_FREQUENCY: Final[int] = 60


class TestAReconstructionHasNoFrames:
    def test_asking_where_a_frame_starts_is_refused(self) -> None:
        source = SampleSource(request=player_sample(SAMPLE_NAME, (), nes_frequency=NTSC_FREQUENCY))

        with pytest.raises(ValueError):
            source.frame_tick(FIRST_FRAME)
