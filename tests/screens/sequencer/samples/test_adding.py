from functools import partial
from typing import Final, List

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.reconstructions import UNTITLED, marked
from automation.steps.sequencer import leave_letting_the_project_go
from sampletones_shared.constants.nes import DEFAULT_NES_FREQUENCY
from tests.screens.sequencer.samples.cases import DOORS, Door
from tests.screens.sequencer.samples.constants import (
    ARRANGED_VOICES,
    ATTEMPTS,
    FREQUENCY_MISMATCH,
    OTHER_RATE,
    SOUND_AT_OTHER_RATE,
    UNSOUND_AT_OTHER_RATE,
    UNSOUND_RECONSTRUCTION,
)
from tests.screens.sequencer.samples.steps import (
    add_anyway,
    add_by_double_click,
    add_from_the_sequencer_browser,
    expect_refused,
    project_part,
)
from tests.suite.screens.worlds.recordings import SHORT_RECONSTRUCTION
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD


class TestAnUnsoundReconstructionAtEveryDoor:
    """A reconstruction that fails as it joins the project is refused with the error notice at every door
    that adds one, and the project stays as it was.

    Each door adds the unsound reconstruction, and the notice names the failure. The same door then adds a
    sound one, and the voices, the history and the title show that it alone joined.
    """

    @pytest.mark.parametrize("door", DOORS, ids=lambda door: door.name)
    def test_it_is_refused_and_a_sound_one_joins(self, screen: Screen, door: Door) -> None:
        """The notice names the failure, and the sound reconstruction joins as the one new voice and entry."""
        voices = screen.sequencer.voices
        history = screen.sequencer.history

        def the_unsound_one_is_refused(screen: Screen) -> None:
            before = history.lines()

            door.add(screen, UNSOUND_RECONSTRUCTION)

            expect_refused(screen)
            assert voices.names() == ARRANGED_VOICES
            assert history.lines() == before
            assert project_part(screen) == ARRANGED_PROJECT.stem

        def the_same_door_adds_a_sound_one(screen: Screen) -> None:
            before = history.lines()

            door.add(screen, SHORT_RECONSTRUCTION)

            screen.expect(
                voices.names,
                [*ARRANGED_VOICES, SHORT_RECONSTRUCTION.stem].__eq__,
                description="the sound reconstruction joined",
            )
            lines = screen.expect(history.lines, lambda lines: len(lines) == len(before) + 1, description="one entry")
            assert SHORT_RECONSTRUCTION.stem in lines[0].words
            assert project_part(screen) == marked(ARRANGED_PROJECT.stem, unsaved=True)

        screen.scenario(
            the_unsound_one_is_refused,
            the_same_door_adds_a_sound_one,
            leave_letting_the_project_go,
        ).run()


class TestAnUnsoundReconstructionAddedAnyway:
    """A reconstruction made at another rate asks about the rate first, and one that fails as it joins is
    refused with the error notice once the reader adds it anyway.

    The project keeps its voices, its history and its rate. The witness adds anyway a sound reconstruction
    made at the same other rate, which joins at the project's rate.
    """

    def test_it_is_refused_after_the_question(self, screen: Screen) -> None:
        """The question names both rates, the notice names the failure, and the sound one then joins."""
        voices = screen.sequencer.voices
        history = screen.sequencer.history
        module = screen.sequencer.module
        question = screen.words(FREQUENCY_MISMATCH).format(reconstruction=OTHER_RATE, project=DEFAULT_NES_FREQUENCY)

        def the_unsound_one_is_refused(screen: Screen) -> None:
            before = history.lines()

            asked = add_anyway(screen, UNSOUND_AT_OTHER_RATE)

            expect_refused(screen)
            assert question in asked
            assert voices.names() == ARRANGED_VOICES
            assert history.lines() == before
            assert module.nes_frequency() == DEFAULT_NES_FREQUENCY
            assert project_part(screen) == ARRANGED_PROJECT.stem

        def a_sound_one_joins_the_same_way(screen: Screen) -> None:
            before = history.lines()

            add_anyway(screen, SOUND_AT_OTHER_RATE)

            screen.expect(
                voices.names,
                [*ARRANGED_VOICES, SOUND_AT_OTHER_RATE.stem].__eq__,
                description="the sound reconstruction joined",
            )
            screen.expect(history.lines, lambda lines: len(lines) == len(before) + 1, description="one entry")
            assert module.nes_frequency() == DEFAULT_NES_FREQUENCY

        screen.scenario(
            the_unsound_one_is_refused,
            a_sound_one_joins_the_same_way,
            leave_letting_the_project_go,
        ).run()


class TestAnUnsoundReconstructionAddedTwice:
    """Each attempt to add a reconstruction that fails as it joins shows the error notice once.

    The unsound reconstruction is added twice through the Sequencer browser's menu, and each attempt shows
    one notice. The witness adds a sound reconstruction the same way.
    """

    def test_each_attempt_shows_one_notice(self, screen: Screen) -> None:
        """One notice stands after each attempt, and the sound one then joins as the one new voice."""
        voices = screen.sequencer.voices
        notice = screen.error_notice

        def each_attempt_is_refused_once(screen: Screen) -> None:
            for _ in range(ATTEMPTS):
                add_from_the_sequencer_browser(screen, UNSOUND_RECONSTRUCTION)
                screen.expect(notice.is_shown, bool, description="the error notice")
                assert len(notice.prompt.shown_windows()) == 1

                expect_refused(screen)

        def a_sound_one_joins_the_same_way(screen: Screen) -> None:
            add_from_the_sequencer_browser(screen, SHORT_RECONSTRUCTION)

            screen.expect(
                voices.names,
                [*ARRANGED_VOICES, SHORT_RECONSTRUCTION.stem].__eq__,
                description="the sound reconstruction joined",
            )

        screen.scenario(
            each_attempt_is_refused_once,
            a_sound_one_joins_the_same_way,
            leave_letting_the_project_go,
        ).run()


class TestAnEmptyProjectRefusingItsFirstSample:
    """An empty project takes the rate of the first reconstruction to join it, and a reconstruction that
    fails as it joins leaves the rate, the history and the title as they were.

    File > New project starts the empty project. The unsound reconstruction made at another rate is
    refused, and the witness adds a sound one made at that rate, which sets the project's rate.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens with nothing loaded, so File > New project starts at once."""
        return Startup(reconstruction=None, project=None)

    def test_a_refused_one_leaves_the_rate(self, screen: Screen) -> None:
        """The rate stays the new project's, and the sound reconstruction then joins and sets its own."""
        voices = screen.sequencer.voices
        history = screen.sequencer.history
        module = screen.sequencer.module

        def start_an_empty_project(screen: Screen) -> None:
            screen.project.create()

            screen.expect(voices.names, [].__eq__, description="an empty project")
            screen.expect(partial(project_part, screen), screen.words(UNTITLED).__eq__, description="the new project")

        def the_unsound_one_is_refused(screen: Screen) -> None:
            rate = module.nes_frequency()
            before = history.lines()

            add_by_double_click(screen, UNSOUND_AT_OTHER_RATE)

            expect_refused(screen)
            assert module.nes_frequency() == rate
            assert history.lines() == before
            assert project_part(screen) == screen.words(UNTITLED)

        def a_sound_one_sets_the_rate(screen: Screen) -> None:
            add_by_double_click(screen, SOUND_AT_OTHER_RATE)

            screen.expect(voices.names, [SOUND_AT_OTHER_RATE.stem].__eq__, description="the sound reconstruction")
            assert module.nes_frequency() == OTHER_RATE

        screen.scenario(
            start_an_empty_project,
            the_unsound_one_is_refused,
            a_sound_one_sets_the_rate,
            leave_letting_the_project_go,
        ).run()
