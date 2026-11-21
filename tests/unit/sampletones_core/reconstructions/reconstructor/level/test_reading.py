from typing import Dict, Final, List, Mapping

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.level import FrameReading, TriangleReader
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

from ..conftest import rendered_audio

BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HALF: Final[float] = 0.5
FULL: Final[float] = 1.0
DRIVE: Final[float] = 2.0
LEVEL_TOLERANCE: Final[float] = 0.05
HELD_FRAMES: Final[int] = 48
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]


def _frame(
    config: Config, extractor: FeatureExtractor, notes: Mapping[ChannelName, InstructionUnion], scale: float
) -> Fragment:
    """A frame from the middle of ``notes`` held together, played at ``scale`` of the level they render at.

    The notes are held long enough for the window of the lowest bin a frame reads to lie within them.
    """
    return extractor.extract(rendered_audio(config, notes, HELD_FRAMES) * scale)[HELD_FRAMES // 2]


def _reader(stems: StemsConfig, channels: Dict[ChannelName, GeneratorUnion], matcher: FrameMatcher) -> TriangleReader:
    layout = StemLayout.of(stems.entries[0], channels)
    catalogs: Dict[GeneratorClassName, KindCatalog] = {
        slot.kind: KindCatalog.build(matcher.candidate_provider, channels[slot.channel_name]) for slot in layout.slots
    }
    return TriangleReader.of(layout, catalogs, matcher)


def _read(reader: TriangleReader, fragment: Fragment) -> FrameReading:
    reading = reader.read(fragment)
    assert reading is not None
    return reading


@pytest.fixture(name="reader", scope="module")
def reader_fixture(all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher) -> TriangleReader:
    return _reader(StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels, joint_matcher)


class TestTheTriangleReader:
    def test_a_bass_on_the_triangle_reads_the_level_it_plays_at(
        self, config: Config, extractor: FeatureExtractor, reader: TriangleReader
    ) -> None:
        reading = _read(reader, _frame(config, extractor, {ChannelName.TRIANGLE: BASS}, HALF))

        assert reading.level == pytest.approx(HALF, rel=LEVEL_TOLERANCE)
        assert reading.note == BASS.pitch

    def test_a_bass_under_a_lead_reads_its_own_level(
        self, config: Config, extractor: FeatureExtractor, reader: TriangleReader
    ) -> None:
        notes = {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD}

        reading = _read(reader, _frame(config, extractor, notes, FULL))

        assert reading.level == pytest.approx(FULL, rel=LEVEL_TOLERANCE)
        assert reading.note == BASS.pitch

    def test_a_stem_driving_the_triangle_harder_reads_against_the_level_it_plays_it_at(
        self,
        config: Config,
        extractor: FeatureExtractor,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        settings = StemSettings.covering(EVERY_CHANNEL).with_drive(ChannelName.TRIANGLE, DRIVE)
        reader = _reader(StemsConfig.single_entry(settings), all_channels, joint_matcher)

        reading = _read(reader, _frame(config, extractor, {ChannelName.TRIANGLE: BASS}, FULL / DRIVE))

        assert reading.level == pytest.approx(FULL, rel=LEVEL_TOLERANCE)

    def test_a_stem_without_the_triangle_has_no_level_to_read(
        self, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
    ) -> None:
        with pytest.raises(ValueError):
            _reader(StemsConfig.single_entry(StemSettings.covering(PULSES)), all_channels, joint_matcher)
