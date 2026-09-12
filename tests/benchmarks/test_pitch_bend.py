from typing import Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import PulseInstruction
from tests.suite.timing import seconds

FRAMES: Final[int] = 6000
PITCH: Final[int] = 60
VOLUME: Final[int] = 12
BEND_OVERHEAD_LIMIT: Final[float] = 1.25


def _stream(bent: bool) -> List[PulseInstruction]:
    """One channel's frames, every one of them bent or none of them."""
    return [
        PulseInstruction(
            on=True,
            pitch=PITCH,
            volume=VOLUME,
            duty_cycle=frame % 4,
            detune=(frame % 21) - 10 if bent else 0,
        )
        for frame in range(FRAMES)
    ]


def _render_seconds(config: Config, instructions: List[PulseInstruction]) -> float:
    """What one render of the stream costs, the reading least disturbed by other load."""
    return seconds(lambda: render_instructions(instructions, ChannelName.PULSE1, config))


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


class TestBendingCostsNothingToRender:
    """A bend moves the divider a frame loads, which is the same work as loading it unbent.

    The reading is a ratio against the same render without a bend, since what a machine renders
    a frame in is its own. What the bound catches is a bend that made rendering a different
    kind of work — a per-frame table rebuild, a lost cache, a fallback path.
    """

    def test_a_bent_stream_renders_in_what_an_unbent_one_takes(self, config: Config) -> None:
        unbent = _render_seconds(config, _stream(bent=False))
        bent = _render_seconds(config, _stream(bent=True))

        assert bent < unbent * BEND_OVERHEAD_LIMIT, f"unbent {unbent:.4f}s, bent {bent:.4f}s"
