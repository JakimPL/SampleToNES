from typing import Final, List

from tests.screens.sequencer.samples.constants import (
    ARRANGED_VOICES,
    LINE_POSITION,
    PLACEHOLDER_START,
    REPLACE_SAMPLE,
    UNSOUND_RECONSTRUCTION,
)
from tests.screens.sequencer.samples.steps import (
    expect_refused,
    leave_unchanged,
    listed_row,
    project_part,
    replace_entry,
    replace_from_the_sequencer_browser,
)
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import marked
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, voice_row
from tests.suite.screens.worlds.recordings import SHORT_RECONSTRUCTION
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD

LINE_LABEL: Final[str] = f"{LINE_POSITION}: {LINE}"


class TestReplacingWithAnUnsoundReconstruction:
    """Replacing a sample with a reconstruction that fails as it joins is refused with the error notice, and
    the sample keeps its name and its sound.

    The Line sample is replaced with the unsound reconstruction from the Sequencer's browser. The witness
    replaces it with a sound one, which takes its place and its name.
    """

    def test_it_is_refused_and_a_sound_one_takes_its_place(self, screen: Screen) -> None:
        """The notice names the failure, and the sound reconstruction then takes the sample's place as one
        entry.
        """
        voices = screen.sequencer.voices
        history = screen.sequencer.history

        def the_unsound_one_is_refused(screen: Screen) -> None:
            before = history.lines()

            replace_from_the_sequencer_browser(screen, UNSOUND_RECONSTRUCTION, voice=LINE, label=LINE_LABEL)

            expect_refused(screen)
            assert voices.names() == ARRANGED_VOICES
            assert history.lines() == before
            assert project_part(screen) == ARRANGED_PROJECT.stem

        def a_sound_one_takes_its_place(screen: Screen) -> None:
            before = history.lines()

            replace_from_the_sequencer_browser(screen, SHORT_RECONSTRUCTION, voice=LINE, label=LINE_LABEL)

            screen.expect(
                voices.names,
                [SHORT_RECONSTRUCTION.stem, BASS_VOICE, PAD].__eq__,
                description="the sound reconstruction in the sample's place",
            )
            screen.expect(history.lines, lambda lines: len(lines) == len(before) + 1, description="one entry")
            assert project_part(screen) == marked(ARRANGED_PROJECT.stem, unsaved=True)

        screen.scenario(
            the_unsound_one_is_refused,
            a_sound_one_takes_its_place,
            leave_letting_the_project_go,
        ).run()


class TestReplaceIsOfferedForSamples:
    """A browser row's menu offers to replace the picked voice only while that voice is a sample.

    With the Pad instrument picked, the menu of a reconstruction's row offers no Replace entry. The witness
    picks the Line sample, and the same menu offers to replace it.
    """

    def test_an_instrument_picked_offers_no_replace(self, screen: Screen) -> None:
        """No entry of the menu reads as a replacement while Pad is picked, and the one naming Line stands once
        Line is."""
        voices = screen.sequencer.voices
        browser = screen.sequencer.browser
        menu = screen.context_menu
        replacing = screen.words(REPLACE_SAMPLE).partition(PLACEHOLDER_START)[0]

        def offered_with(name: str) -> List[str]:
            voices.pick(voice_row(screen, name))
            browser.right_click(listed_row(screen, browser, SHORT_RECONSTRUCTION))
            screen.expect(menu.is_shown, bool, description=f"the row's menu with {name} picked")
            labels = menu.labels()
            menu.dismiss()
            screen.expect(menu.is_shown, lambda shown: not shown, description="the menu put away")
            return labels

        def only_a_sample_is_offered(screen: Screen) -> None:
            with_the_instrument = offered_with(PAD)
            with_the_sample = offered_with(LINE)

            assert not [label for label in with_the_instrument if label.startswith(replacing)]
            assert replace_entry(screen, LINE_LABEL) in with_the_sample

        screen.scenario(
            only_a_sample_is_offered,
            lambda screen: leave_unchanged(screen, ARRANGED_PROJECT.stem),
        ).run()
