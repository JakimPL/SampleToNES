from pathlib import Path

import pytest

from sampletones_application.logic.sequencer.channels import SequencerChannelsLogic
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.famitracker.export import write_ftm
from sampletones_core.famitracker.specification.channels import ChannelId
from sampletones_core.famitracker.specification.file import FTM_VERSION
from sampletones_core.famitracker.specification.sequences import SequenceKind
from sampletones_core.project.project import Project
from tests.suite.famitracker import ParsedModule, parse_ftm

EXPECTED_INSTRUMENT_COUNT = 5  # kick -> pulse1 + triangle (2); hihat -> pulse1 + pulse2 + noise (3)
PLAYED_CHANNELS = {
    int(ChannelId.SQUARE1),
    int(ChannelId.SQUARE2),
    int(ChannelId.TRIANGLE),
    int(ChannelId.NOISE),
}


@pytest.fixture
def parsed_module(integration_project: Project, module_path: Path) -> ParsedModule:
    write_ftm(module_path, integration_project)
    return parse_ftm(module_path.read_bytes())


class TestFtmPipeline:
    """End-to-end: synthesized + reconstructed samples -> Project -> `.ftm` -> parse."""

    def test_writes_a_parseable_module_file(self, integration_project: Project, module_path: Path) -> None:
        write_ftm(module_path, integration_project)
        assert module_path.exists()
        assert parse_ftm(module_path.read_bytes()).version == FTM_VERSION

    def test_instrument_count_covers_every_slice(self, parsed_module: ParsedModule) -> None:
        assert len(parsed_module.instruments) == EXPECTED_INSTRUMENT_COUNT

    def test_order_dimensions(self, parsed_module: ParsedModule) -> None:
        assert parsed_module.frames.frame_count == 2
        assert all(len(entry) == 5 for entry in parsed_module.frames.order)

    def test_patterns_cover_the_played_channels(self, parsed_module: ParsedModule) -> None:
        assert {pattern.channel for pattern in parsed_module.patterns} == PLAYED_CHANNELS

    def test_module_carries_audible_volume(self, parsed_module: ParsedModule) -> None:
        volume_sequences = [
            sequence for sequence in parsed_module.sequences if sequence.sequence_type == int(SequenceKind.VOLUME)
        ]
        assert any(any(item > 0 for item in sequence.items) for sequence in volume_sequences)


class TestSilencedChannelsReachTheModuleWhole:
    """A silenced channel belongs to the listening session, so the module still carries it.

    The mute set lives in the application's channels logic while the writer reads the project
    alone. These read that from the outside: a module exported while channels are silenced holds
    every played channel, and is the very file the full mix writes.
    """

    def test_a_soloed_mix_writes_every_played_channel(
        self,
        integration_project: Project,
        module_path: Path,
    ) -> None:
        channels = SequencerChannelsLogic()
        channels.solo(GeneratorName.TRIANGLE)
        assert channels.active_channels == frozenset({GeneratorName.TRIANGLE})

        write_ftm(module_path, integration_project)

        assert {pattern.channel for pattern in parse_ftm(module_path.read_bytes()).patterns} == PLAYED_CHANNELS

    def test_a_fully_silenced_mix_writes_the_same_file(
        self,
        integration_project: Project,
        module_path: Path,
        tmp_path: Path,
    ) -> None:
        full_mix_path = tmp_path / "full_mix.ftm"
        write_ftm(full_mix_path, integration_project)
        channels = SequencerChannelsLogic()
        channels.mute_all()
        assert channels.active_channels == frozenset()

        write_ftm(module_path, integration_project)

        assert module_path.read_bytes() == full_mix_path.read_bytes()
