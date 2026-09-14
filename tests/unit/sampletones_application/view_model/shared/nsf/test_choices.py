from dataclasses import dataclass
from typing import Callable, Final

import pytest

from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.offer import FIRST_FRAME
from sampletones_application.view_model.shared.nsf.repeat import NSFRepeat
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.project import Project
from sampletones_player.builder import SONG_START
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.export.program import NSFProgram
from sampletones_player.nsf.information import NSFInformation, fit_field
from sampletones_player.specification.nsf import STRING_TEXT_SIZE
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.nsf import (
    PROGRAM_ARTIST,
    PROGRAM_TITLE,
    SAMPLE_CHANNELS,
    project_offer,
    sample_offer,
    standing_choices,
)

OVERLONG_TEXT: Final[str] = "Ünïcödé " * STRING_TEXT_SIZE
LATER_FRAME: Final[int] = 3


class TestTheTextFitsItsField(BaseTestSuite):
    """A typed text is held as the part of it the header field carries, so the dialog shows what
    the file will list."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        edit: Callable[[NSFExportChoices, str], NSFExportChoices]
        read: Callable[[NSFInformation], str]

    test_cases = (
        TestCase(
            label="title",
            edit=NSFExportChoices.with_title,
            read=lambda information: information.title,
        ),
        TestCase(
            label="artist",
            edit=NSFExportChoices.with_artist,
            read=lambda information: information.artist,
        ),
        TestCase(
            label="copyright",
            edit=NSFExportChoices.with_copyright,
            read=lambda information: information.copyright,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_an_overlong_text_is_cut_by_the_fields_rule(self, test_case: TestCase) -> None:
        edited = test_case.edit(standing_choices(project_offer()), OVERLONG_TEXT)

        assert test_case.read(edited.information) == fit_field(OVERLONG_TEXT)

    def test_editing_one_field_keeps_the_others(self) -> None:
        choices = standing_choices(project_offer())

        edited = choices.with_copyright(PROGRAM_ARTIST)

        assert edited.information.title == PROGRAM_TITLE
        assert edited.information.artist == PROGRAM_ARTIST
        assert edited.information.copyright == PROGRAM_ARTIST


class TestAChannelIsTickedAmongTheSounded:
    def test_unticking_a_channel_rests_it(self) -> None:
        offer = project_offer()

        edited = standing_choices(offer).with_channel(ChannelName.NOISE, False, offer)

        assert ChannelName.NOISE not in edited.channels

    def test_ticking_a_channel_sounds_it_again(self) -> None:
        offer = project_offer()
        choices = standing_choices(offer).with_channel(ChannelName.NOISE, False, offer)

        edited = choices.with_channel(ChannelName.NOISE, True, offer)

        assert edited.channels == frozenset(offer.channels)

    def test_a_channel_the_source_leaves_silent_stays_unticked(self) -> None:
        offer = sample_offer()

        edited = standing_choices(offer).with_channel(ChannelName.NOISE, True, offer)

        assert edited.channels == frozenset(SAMPLE_CHANNELS)

    def test_choices_with_no_channel_write_no_program(self) -> None:
        offer = sample_offer()
        choices = standing_choices(offer)
        for channel in SAMPLE_CHANNELS:
            choices = choices.with_channel(channel, False, offer)

        assert not choices.writable


class TestTheLoopFrameStaysInTheOrder(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        frame: int

    test_cases = (
        TestCase(label="before_the_first", frame=FIRST_FRAME - 1, expected=FIRST_FRAME),
        TestCase(label="within", frame=LATER_FRAME, expected=LATER_FRAME),
        TestCase(label="past_the_last", frame=project_offer().frame_count, expected=project_offer().last_frame),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_frame_is_brought_within_the_order(self, test_case: TestCase) -> None:
        offer = project_offer()

        edited = standing_choices(offer).with_loop_frame(test_case.frame, offer)

        assert edited.loop_frame == test_case.expected


class TestTheSourceBoundsTheChoices:
    def test_a_song_laid_out_in_frames_repeats_from_one(self) -> None:
        offer = project_offer()

        edited = standing_choices(offer).with_repeat(NSFRepeat.FROM_FRAME, offer)

        assert edited.repeat == NSFRepeat.FROM_FRAME

    def test_a_reconstruction_keeps_its_repeat_off_the_frames(self) -> None:
        offer = sample_offer()

        edited = standing_choices(offer).with_repeat(NSFRepeat.FROM_FRAME, offer)

        assert edited.repeat == NSFRepeat.FROM_START

    def test_a_project_compresses_with_its_instruments(self) -> None:
        offer = project_offer()

        edited = standing_choices(offer).with_scheme(CompressionScheme.INSTRUMENTS, offer)

        assert edited.scheme == CompressionScheme.INSTRUMENTS

    def test_a_reconstruction_keeps_to_the_schemes_that_write_it_differently(self) -> None:
        offer = sample_offer()
        choices = standing_choices(offer)

        edited = choices.with_scheme(CompressionScheme.INSTRUMENTS, offer)

        assert edited.scheme == choices.scheme


class TestTheDialogOpensOnTheStatedProgram:
    def test_a_project_opens_on_the_program_it_is_written_as(self) -> None:
        program = NSFProgram.for_project(Project.create(title=PROGRAM_TITLE, author=PROGRAM_ARTIST))

        choices = NSFExportChoices.initial(program, project_offer())

        assert choices.information == program.information
        assert choices.channels == program.channels
        assert choices.repeat == NSFRepeat.FROM_START
        assert choices.scheme == program.scheme

    def test_the_channels_narrow_to_the_ones_the_source_sounds(self) -> None:
        program = NSFProgram.for_project(Project.create())

        choices = NSFExportChoices.initial(program, sample_offer())

        assert choices.channels == frozenset(SAMPLE_CHANNELS)

    def test_a_program_stopping_at_its_end_opens_playing_once(self) -> None:
        program = NSFProgram.for_project(Project.create()).model_copy(update={"loop_tick": None})

        choices = NSFExportChoices.initial(program, sample_offer())

        assert choices.repeat == NSFRepeat.ONCE

    def test_a_program_repeating_from_later_in_the_song_is_refused(self) -> None:
        program = NSFProgram.for_project(Project.create()).model_copy(update={"loop_tick": SONG_START + 1})

        with pytest.raises(ValueError):
            NSFExportChoices.initial(program, project_offer())
