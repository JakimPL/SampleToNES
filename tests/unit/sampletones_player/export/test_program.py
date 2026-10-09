from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ALL_CHANNELS, ChannelName
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.project.project import Project
from sampletones_player.builder import SONG_START, loop_tick_from_instruments
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.export.program import (
    DEFAULT_SCHEME,
    NO_ARTIST,
    NSFProgram,
)
from sampletones_player.nsf.information import NSFInformation
from sampletones_shared.application import SAMPLETONES_COPYRIGHT
from tests.suite.player import (
    PLAYER_REFERENCE_PITCH,
    player_features,
    player_instrument,
    player_sample,
)

NTSC_FREQUENCY: Final[int] = 60
SOUNDING_TICKS: Final[int] = 6
PROJECT_TITLE: Final[str] = "Demo"
PROJECT_AUTHOR: Final[str] = "Jakim"
SAMPLE_NAME: Final[str] = "Amen"


def lead(loop: bool) -> InstrumentExport:
    return player_instrument(
        "lead",
        ChannelName.PULSE1,
        player_features(SOUNDING_TICKS, PLAYER_REFERENCE_PITCH, duty_cycle=True),
        nes_frequency=NTSC_FREQUENCY,
        loop=loop,
    )


def sample(loop: bool) -> SampleExport:
    return player_sample(SAMPLE_NAME, (lead(loop),), nes_frequency=NTSC_FREQUENCY)


@pytest.fixture(name="project")
def project_fixture() -> Project:
    return Project.create(title=PROJECT_TITLE, author=PROJECT_AUTHOR)


class TestTheProgramAProjectStates:
    """What a composition is written as when nobody chose otherwise."""

    def test_it_is_listed_under_the_projects_title_and_author(self, project: Project) -> None:
        assert NSFProgram.for_project(project).information == NSFInformation(
            title=PROJECT_TITLE,
            artist=PROJECT_AUTHOR,
            copyright=SAMPLETONES_COPYRIGHT,
        )

    def test_it_sounds_every_channel(self, project: Project) -> None:
        assert NSFProgram.for_project(project).channels == ALL_CHANNELS

    def test_it_repeats_from_its_first_tick(self, project: Project) -> None:
        assert NSFProgram.for_project(project).loop_tick == SONG_START

    def test_it_is_compressed_under_the_default_scheme(self, project: Project) -> None:
        assert NSFProgram.for_project(project).scheme == DEFAULT_SCHEME


class TestTheProgramASampleStates:
    """What a reconstruction's slices are written as when nobody chose otherwise."""

    def test_it_is_listed_under_the_reconstructions_name_credited_to_nobody(
        self,
    ) -> None:
        information = NSFProgram.for_sample(sample(loop=False)).information
        assert (information.title, information.artist) == (
            SAMPLE_NAME,
            NO_ARTIST,
        )

    def test_it_sounds_every_channel(self) -> None:
        assert NSFProgram.for_sample(sample(loop=False)).channels == ALL_CHANNELS

    @pytest.mark.parametrize("loop", [True, False], ids=["repeating", "played once"])
    def test_it_repeats_where_every_slice_repeats(self, loop: bool) -> None:
        request = sample(loop)
        assert NSFProgram.for_sample(request).loop_tick == loop_tick_from_instruments(request.instruments)


class TestWhatAProgramHolds:
    """A program states choices a file can carry."""

    def test_a_program_sounding_no_channel_is_refused(self, project: Project) -> None:
        with pytest.raises(ValidationError):
            NSFProgram.model_validate(NSFProgram.for_project(project).model_dump() | {"channels": frozenset()})

    def test_a_loop_before_the_song_starts_is_refused(self, project: Project) -> None:
        with pytest.raises(ValidationError):
            NSFProgram.model_validate(NSFProgram.for_project(project).model_dump() | {"loop_tick": -1})

    def test_a_program_may_play_once(self, project: Project) -> None:
        program = NSFProgram.model_validate(NSFProgram.for_project(project).model_dump() | {"loop_tick": None})
        assert program.loop_tick is None

    @pytest.mark.parametrize("scheme", list(CompressionScheme), ids=str)
    def test_every_scheme_is_a_choice(self, project: Project, scheme: CompressionScheme) -> None:
        program = NSFProgram.model_validate(NSFProgram.for_project(project).model_dump() | {"scheme": scheme})
        assert program.scheme == scheme
