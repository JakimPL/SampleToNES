from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.export.nsf.logic import NSFExportLogic
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.request import SampleExport
from sampletones_core.timing import SongTiming
from sampletones_player.builder import SONG_START
from sampletones_player.compression.scheme import CompressionScheme, offered_schemes
from sampletones_player.export.program import NSFProgram
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.nsf import PROGRAM_TITLE, FakeNSFExportService, FakeProgramBackend
from tests.suite.player import PLAYER_REFERENCE_PITCH, player_features, player_instrument, player_sample

PROJECT_NAME: Final[str] = "chiptune"
SAMPLE_NAME: Final[str] = "Amen"
EXTRA_FRAMES: Final[int] = 3
LOOP_FRAME: Final[int] = 2
NTSC_FREQUENCY: Final[int] = 60
SHORT_FRAMES: Final[int] = 8
LONG_FRAMES: Final[int] = 24
CHOSEN_DESTINATION: Final[Path] = Path("/home/user/programs/take one.nsf")


def two_slice_sample() -> SampleExport:
    """A reconstruction sounding a short lead and a longer bass, neither of them repeating."""
    return player_sample(
        SAMPLE_NAME,
        (
            player_instrument(
                "lead",
                ChannelName.PULSE1,
                player_features(SHORT_FRAMES, PLAYER_REFERENCE_PITCH, duty_cycle=True),
                nes_frequency=NTSC_FREQUENCY,
                loop=False,
            ),
            player_instrument(
                "bass",
                ChannelName.TRIANGLE,
                player_features(LONG_FRAMES, PLAYER_REFERENCE_PITCH, duty_cycle=False),
                nes_frequency=NTSC_FREQUENCY,
                loop=False,
            ),
        ),
        nes_frequency=NTSC_FREQUENCY,
    )


class NSFExportFixture:
    """An NSF export setup over a real project, with a service and a backend that record the run."""

    def __init__(self, directory: Path, *, operation_active: bool = False) -> None:
        project_manager = ProjectManager()
        project_manager.session.mark_loaded(PROJECT_NAME)
        self.controller = ProjectController(project_manager)
        for _ in range(EXTRA_FRAMES):
            self.controller.append_frame()

        self.directory = directory
        self.session_manager = MagicMock()
        self.session_manager.get_project_path.return_value = directory
        self.session_manager.get_instrument_path.return_value = directory
        self.service = FakeNSFExportService()
        self.backend = FakeProgramBackend()
        self.views: List[NSFExportViewModel] = []
        self.destinations: List[Path] = []
        self.logic = NSFExportLogic(
            self.controller,
            self.session_manager,
            self.service,
            self.backend,
            is_operation_active=lambda: operation_active,
        )
        self.logic.on_view_changed = self.views.append
        self.logic.on_choose_destination = self.destinations.append

    @property
    def view(self) -> NSFExportViewModel:
        assert self.views, "A view was expected to be emitted"
        return self.views[-1]

    def edit(self, choices: NSFExportChoices) -> None:
        self.logic.apply(choices)


@pytest.fixture
def export(tmp_path: Path) -> NSFExportFixture:
    return NSFExportFixture(tmp_path)


class TestOfferingTheProject:
    def test_the_dialog_opens_on_a_file_named_after_the_project(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        assert export.view.destination == export.directory / f"{PROJECT_NAME}{EXT_FILE_NSF}"

    def test_the_dialog_opens_on_the_program_the_project_is_written_as(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        program = NSFProgram.for_project(export.controller.project)
        assert export.view.choices == NSFExportChoices.initial(program, export.view.offer)

    def test_every_channel_frame_and_scheme_is_offered(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        offer = export.view.offer
        assert offer.channels == tuple(ChannelName.items())
        assert offer.frame_count == export.controller.order_length
        assert offer.schemes == offered_schemes(seeded=True)

    def test_the_length_is_the_whole_orders(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        project = export.controller.project
        assert export.view.ticks == SongTiming.from_project(project).frame_tick(project.song.order_length())
        assert export.view.nes_frequency == project.settings.nes_frequency

    def test_the_setup_occupies_the_application_from_the_dialog_opening(self, export: NSFExportFixture) -> None:
        assert not export.logic.is_active

        assert export.logic.open_project()

        assert export.logic.is_active

    def test_another_exclusive_operation_holds_the_dialog_closed(self, tmp_path: Path) -> None:
        export = NSFExportFixture(tmp_path, operation_active=True)

        assert not export.logic.open_project()
        assert not export.logic.is_active
        assert not export.views

    def test_closing_releases_the_application(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        export.logic.close()

        assert not export.logic.is_active


class TestOfferingASample:
    def test_the_channels_are_the_ones_the_slices_sound_on(self, export: NSFExportFixture) -> None:
        export.logic.open_sample(two_slice_sample())

        assert export.view.channels == (ChannelName.PULSE1, ChannelName.TRIANGLE)
        assert NSFRepeat.FROM_FRAME not in export.view.repeats
        assert export.view.schemes == offered_schemes(seeded=False)

    def test_the_dialog_opens_on_a_file_named_after_the_reconstruction(self, export: NSFExportFixture) -> None:
        export.logic.open_sample(two_slice_sample())

        assert export.view.destination == export.directory / f"{SAMPLE_NAME}{EXT_FILE_NSF}"

    def test_the_song_lasts_as_long_as_the_longest_sounding_slice(self, export: NSFExportFixture) -> None:
        export.logic.open_sample(two_slice_sample())
        assert export.view.ticks == LONG_FRAMES

        export.edit(export.view.choices.with_channel(ChannelName.TRIANGLE, False, export.view.offer))

        assert export.view.ticks == SHORT_FRAMES


class TestTheDestination:
    def test_the_destination_is_asked_for_from_where_it_stands(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        export.logic.request_destination()

        assert export.destinations == [export.view.destination]

    def test_a_chosen_destination_is_the_one_written(self, export: NSFExportFixture) -> None:
        export.logic.open_project()
        export.logic.set_destination(CHOSEN_DESTINATION)

        export.logic.start()

        assert export.service.projects[0].destination == CHOSEN_DESTINATION


class TestHandingTheProjectOver:
    def test_the_service_writes_the_project_through_the_chosen_backend(self, export: NSFExportFixture) -> None:
        export.logic.open_project()
        destination = export.view.destination

        assert export.logic.start()

        run = export.service.projects[0]
        assert run.destination == destination
        assert run.backend is export.backend.chosen[0]
        assert run.request == export.controller.export_request

    def test_the_program_carries_the_choices(self, export: NSFExportFixture) -> None:
        export.logic.open_project()
        offer = export.view.offer
        choices = (
            export.view.choices.with_title(PROGRAM_TITLE)
            .with_channel(ChannelName.NOISE, False, offer)
            .with_repeat(NSFRepeat.FROM_FRAME, offer)
            .with_loop_frame(LOOP_FRAME, offer)
            .with_scheme(CompressionScheme.RUNS, offer)
        )
        export.edit(choices)

        export.logic.start()

        program = export.backend.program
        assert program.information == choices.information
        assert program.channels == frozenset(ChannelName.items()) - {ChannelName.NOISE}
        assert program.loop_tick == SongTiming.from_project(export.controller.project).frame_tick(LOOP_FRAME)
        assert program.scheme == CompressionScheme.RUNS

    def test_handing_over_closes_the_setup(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        export.logic.start()

        assert not export.logic.is_active

    def test_a_program_sounding_nothing_stays_in_the_setup(self, export: NSFExportFixture) -> None:
        export.logic.open_project()
        choices = export.view.choices
        for channel in ChannelName.items():
            choices = choices.with_channel(channel, False, export.view.offer)
        export.edit(choices)

        assert not export.logic.start()

        assert not export.service.projects
        assert export.logic.is_active

    def test_the_project_folder_stays_where_the_project_left_it(self, export: NSFExportFixture) -> None:
        export.logic.open_project()

        export.logic.start()

        export.session_manager.set_project_path.assert_not_called()

    def test_an_export_starts_from_the_open_setup_alone(self, export: NSFExportFixture) -> None:
        export.logic.open_project()
        export.logic.start()

        assert not export.logic.start()

        assert len(export.service.projects) == 1


class TestTheRepeatLandsOnTheSongsTicks(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        repeat: NSFRepeat
        expected: Optional[int]

    test_cases = (
        TestCase(label="once", repeat=NSFRepeat.ONCE, expected=None),
        TestCase(label="from_start", repeat=NSFRepeat.FROM_START, expected=SONG_START),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_sample_repeats_where_the_choice_says(self, test_case: TestCase, tmp_path: Path) -> None:
        export = NSFExportFixture(tmp_path)
        export.logic.open_sample(two_slice_sample())
        export.edit(export.view.choices.with_repeat(test_case.repeat, export.view.offer))

        export.logic.start()

        assert export.backend.program.loop_tick == test_case.expected


class TestHandingTheSampleOver:
    def test_the_service_writes_the_slices(self, export: NSFExportFixture) -> None:
        sample = two_slice_sample()
        export.logic.open_sample(sample)

        export.logic.start()

        assert export.service.samples[0].request == sample

    def test_the_next_instrument_export_opens_where_this_one_was_written(self, export: NSFExportFixture) -> None:
        export.logic.open_sample(two_slice_sample())
        export.logic.set_destination(CHOSEN_DESTINATION)

        export.logic.start()

        export.session_manager.set_instrument_path.assert_called_once_with(CHOSEN_DESTINATION.parent)
