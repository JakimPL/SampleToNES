from pathlib import Path

import pytest

from automation.worlds.home import World
from sampletones_shared.constants.nes import DEFAULT_NES_FREQUENCY
from tests.screens.sequencer.samples.constants import (
    OTHER_RATE,
    SOUND_AT_OTHER_RATE,
    UNSOUND_AT_OTHER_RATE,
    UNSOUND_RECONSTRUCTION,
)
from tests.suite.screens.seeds.reconstructions import PlayableReconstruction, UnsoundReconstruction
from tests.suite.screens.worlds.recordings import STEM_FRAMES, STEM_TAKES
from tests.suite.screens.worlds.songs import sequencer_world


@pytest.fixture
def world() -> World:
    """The Sequencer's home, holding besides an unsound reconstruction at the project's rate and at another,
    and a sound one at the other rate.

    Each plays the stem takes the home holds; the unsound ones name all three, and their record states no
    scale, which a record of several recordings always states.
    """
    sequencer = sequencer_world()
    takes = tuple(Path.cwd() / name for name in STEM_TAKES)
    return World(
        state=sequencer.state,
        application_config=None,
        config=None,
        files=(
            *sequencer.files,
            UnsoundReconstruction(UNSOUND_RECONSTRUCTION, takes, STEM_FRAMES, DEFAULT_NES_FREQUENCY),
            UnsoundReconstruction(UNSOUND_AT_OTHER_RATE, takes, STEM_FRAMES, OTHER_RATE),
            PlayableReconstruction(SOUND_AT_OTHER_RATE, takes[:1], STEM_FRAMES, OTHER_RATE),
        ),
    )
