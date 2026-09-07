from pathlib import Path
from typing import Tuple

from sampletones_application.logic.main.converter.destination import Destination
from sampletones_core.configs import Config
from tests.suite.base import BaseTestSuite


class TestTheDocumentARunIsMaking(BaseTestSuite):
    """A run of one names itself after the reconstruction it writes."""

    def test_the_output_names_the_reconstruction(self) -> None:
        destination = Destination(
            input_path=Path("/audio/kick.wav"),
            output_path=Path("/reconstructions/track.stn"),
            is_file=True,
        )

        assert destination.reconstruction_name == "track"

    def test_a_run_yet_to_resolve_its_output_names_the_recording_picked(self) -> None:
        destination = Destination(input_path=Path("/audio/kick.wav"), output_path=None, is_file=True)

        assert destination.reconstruction_name == "kick"

    def test_a_converter_aimed_at_nothing_names_nothing(self) -> None:
        assert Destination.unset().reconstruction_name == ""

    def test_a_completed_run_names_what_it_wrote(self) -> None:
        written = Path("/reconstructions/mixed.stn")
        destination = Destination.unset().writing_to(written)

        assert (destination.output_path, destination.reconstruction_name) == (written, "mixed")


class TestWhereAMixWrites(BaseTestSuite):
    def test_a_mix_with_nobody_taking_part_stands_where_it_was(self) -> None:
        destination = Destination.unset()
        sources: Tuple[Path, ...] = ()

        assert destination.aimed_at_mix(Config(), sources, frozenset()) == destination
