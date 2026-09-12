from dataclasses import dataclass
from typing import Dict, Final, List, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.generation import GenerationConfig
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.instructions import PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate
from sampletones_core.reconstructions.reconstructor.refinement import refiner
from sampletones_core.reconstructions.reconstructor.refinement.refiner import PitchRefiner
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TONES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]
PITCH: Final[int] = 60
VOLUME: Final[int] = 12
FRAMES: Final[int] = 4
BEND: Final[int] = 3
SECONDS: Final[float] = 0.2
STEM_A: Final[int] = 0
STEM_B: Final[int] = 1


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


def _stems(*entries: StemEntry) -> StemsConfig:
    """A setup naming ``entries`` on one precedence level."""
    return StemsConfig(
        entries=list(entries),
        hierarchy=StemsHierarchy(levels=[[entry.id for entry in entries]]),
        channel_cap=len(TONES),
    )


def _recording(config: Config, channel_name: ChannelName) -> np.ndarray:
    """A steady tone standing a little off the note ``PITCH`` names, so a reading has room to move."""
    generator = get_generators_by_channels(config, TONES)[channel_name]
    sample_rate = config.library.sample_rate
    frequency = generator.sounds_at(PITCH, BEND)

    count = int(sample_rate * SECONDS)
    phase = (np.arange(count) * frequency / sample_rate) % 1.0
    return np.where(phase < 0.5, 0.4, -0.4).astype(np.float64)


def _stream(channel_name: ChannelName) -> List[ScoredCandidate]:
    """One channel's frames, each sounding the note the matching chose and no bend."""
    instruction = (
        PulseInstruction(on=True, pitch=PITCH, volume=VOLUME, duty_cycle=2)
        if channel_name is ChannelName.PULSE1
        else TriangleInstruction(on=True, pitch=PITCH)
    )
    return [ScoredCandidate(instruction=instruction, cost=0.0, approximation=np.zeros(1)) for _ in range(FRAMES)]


def _bends(streams: Dict[ChannelName, List[ScoredCandidate]], channel_name: ChannelName) -> List[int]:
    return [candidate.instruction.timer_offset for candidate in streams[channel_name]]


def _refine(
    config: Config,
    stems: StemsConfig,
    stem_ids: Dict[ChannelName, List[int]],
) -> Dict[ChannelName, List[ScoredCandidate]]:
    refined = PitchRefiner(
        config=config,
        channels=get_generators_by_channels(config, TONES),
        stems=stems,
    )
    return refined.refine(
        {channel_name: _stream(channel_name) for channel_name in TONES},
        stem_ids,
        {STEM_A: _recording(config, ChannelName.PULSE1)},
    )


class TestWhichChannelsAStemCarries(BaseTestSuite):
    """A stem states the channels it bends, and the refinement acts on those alone.

    The same recording reaches both channels of one stem here, so what separates them is only
    what the entry names — which is the whole of the switch.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        bends: Tuple[ChannelName, ...]
        bent: Tuple[ChannelName, ...]

    test_cases: Tuple["TestWhichChannelsAStemCarries.TestCase", ...] = (
        TestCase(label="both channels", bends=tuple(TONES), bent=tuple(TONES)),
        TestCase(label="the pulse alone", bends=(ChannelName.PULSE1,), bent=(ChannelName.PULSE1,)),
        TestCase(label="the triangle alone", bends=(ChannelName.TRIANGLE,), bent=(ChannelName.TRIANGLE,)),
        TestCase(label="neither channel", bends=(), bent=()),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_only_the_channels_the_stem_names_are_carried(
        self,
        config: Config,
        test_case: "TestWhichChannelsAStemCarries.TestCase",
    ) -> None:
        stems = _stems(StemEntry(id=STEM_A, settings=StemSettings(channels=TONES, bends=list(test_case.bends))))
        streams = _refine(config, stems, {channel_name: [STEM_A] * FRAMES for channel_name in TONES})

        for channel_name in TONES:
            bends = _bends(streams, channel_name)
            if channel_name in test_case.bent:
                assert any(bends), f"{channel_name} was named and stayed at its note"
            else:
                assert not any(bends), f"{channel_name} was left out and moved anyway"


class TestWhatTheRefinementReadsPerStem:
    """A reading is taken for the recording a bend is read from, and for no other."""

    @staticmethod
    def _counted(monkeypatch: pytest.MonkeyPatch) -> List[int]:
        readings: List[int] = []

        def counting(recording: np.ndarray, sample_rate: int, hop_length: int) -> refiner.InstantaneousPitch:
            readings.append(len(recording))
            return refiner.InstantaneousPitch(recording, sample_rate, hop_length)

        monkeypatch.setattr(refiner, "InstantaneousPitch", counting)
        return readings

    def test_a_stem_carrying_nothing_is_never_read(
        self,
        config: Config,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        readings = self._counted(monkeypatch)
        stems = _stems(
            StemEntry(id=STEM_A, settings=StemSettings(channels=TONES, bends=[])),
            StemEntry(id=STEM_B, settings=StemSettings(channels=TONES, bends=list(TONES))),
        )
        _refine(config, stems, {channel_name: [STEM_A] * FRAMES for channel_name in TONES})

        assert not readings

    def test_a_frame_no_stem_took_is_left_at_its_note(self, config: Config) -> None:
        """A resting frame names no recording, so there is nothing to read a bend out of."""
        stems = _stems(StemEntry(id=STEM_A, settings=StemSettings(channels=TONES, bends=list(TONES))))
        resting = {channel_name: [RESTING_STEM_ID] * FRAMES for channel_name in TONES}
        streams = _refine(config, stems, resting)

        assert not any(_bends(streams, ChannelName.PULSE1))
        assert not any(_bends(streams, ChannelName.TRIANGLE))
