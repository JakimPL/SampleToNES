from pathlib import Path

from sampletones_core.famitracker.export import write_ftm
from sampletones_core.famitracker.specification.channels import ChannelId
from sampletones_core.famitracker.specification.file import FTM_VERSION
from sampletones_core.project.project import Project
from tests.unit.sampletones_core.famitracker.reader import parse_ftm

EXPECTED_INSTRUMENT_COUNT = 5  # kick -> pulse1 + triangle (2); hihat -> pulse1 + pulse2 + noise (3)
PLAYED_CHANNELS = {
    int(ChannelId.SQUARE1),
    int(ChannelId.SQUARE2),
    int(ChannelId.TRIANGLE),
    int(ChannelId.NOISE),
}


class TestFtmPipeline:
    """End-to-end: synthesized + reconstructed samples -> Project -> `.ftm` -> parse."""

    def test_writes_a_parseable_module_file(self, integration_project: Project, tmp_path: Path) -> None:
        path = tmp_path / "drums.ftm"
        write_ftm(path, integration_project)
        assert path.exists()

        parsed = parse_ftm(path.read_bytes())
        assert parsed.version == FTM_VERSION

    def test_instrument_count_covers_every_slice(self, integration_project: Project, tmp_path: Path) -> None:
        path = tmp_path / "drums.ftm"
        write_ftm(path, integration_project)
        parsed = parse_ftm(path.read_bytes())
        assert len(parsed.instruments) == EXPECTED_INSTRUMENT_COUNT

    def test_order_dimensions(self, integration_project: Project, tmp_path: Path) -> None:
        path = tmp_path / "drums.ftm"
        write_ftm(path, integration_project)
        parsed = parse_ftm(path.read_bytes())
        assert parsed.frames.frame_count == 2
        assert all(len(entry) == 5 for entry in parsed.frames.order)

    def test_patterns_cover_the_played_channels(self, integration_project: Project, tmp_path: Path) -> None:
        path = tmp_path / "drums.ftm"
        write_ftm(path, integration_project)
        parsed = parse_ftm(path.read_bytes())
        assert {pattern.channel for pattern in parsed.patterns} == PLAYED_CHANNELS
