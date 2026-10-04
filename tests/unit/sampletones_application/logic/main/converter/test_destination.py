from pathlib import Path
from typing import Final

from sampletones_application.logic.main.converter.destination import Destination
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.converter import BatchConversion, BatchEntry, GroupConversion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite

_PULSE: Final[StemsConfig] = StemsConfig.single_entry(StemSettings.covering([ChannelName.PULSE1]))
_TRIANGLE: Final[StemsConfig] = StemsConfig.single_entry(StemSettings.covering([ChannelName.TRIANGLE]))


class TestWhereARunWrites(BaseTestSuite):
    """The destination names what the run's plan names, and a run with no plan names nothing new."""

    def test_a_completed_run_names_what_it_wrote(self) -> None:
        written = Path("/reconstructions/mixed.stn")

        assert Destination.unset().writing_to(written).output_path == written

    def test_a_run_with_nobody_taking_part_stands_where_it_was(self) -> None:
        destination = Destination.unset().writing_to(Path("/reconstructions/earlier.stn"))

        assert destination.aimed_at(Config(), None) == destination

    def test_a_mix_names_the_file_its_plan_writes(self, tmp_path: Path) -> None:
        config = Config()
        plan = GroupConversion(sources=(tmp_path / "a.wav", tmp_path / "b.wav"), stems=_PULSE)

        assert Destination.unset().aimed_at(config, plan).output_path == plan.destination(config)

    def test_a_batch_names_the_folder_holding_what_its_plan_writes(self, tmp_path: Path) -> None:
        config = Config()
        plan = BatchConversion(
            entries=(
                BatchEntry(source=tmp_path / "lead.wav", stems=_PULSE, base_directory=None),
                BatchEntry(source=tmp_path / "bass.wav", stems=_TRIANGLE, base_directory=None),
            )
        )

        output_path = Destination.unset().aimed_at(config, plan).output_path

        assert output_path == plan.destination(config)
        assert all(output_path in job.output_path.parents for job in plan.jobs(config))
