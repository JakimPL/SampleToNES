import operator
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.application import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import (
    edit_envelope,
    expect_open,
    marked,
    raise_the_first_level,
    titled,
    voice_title,
)
from tests.suite.screens.steps.sequencer import double_click_voice, open_voice, voice_row
from tests.suite.screens.world import OPEN_RECONSTRUCTION, SONG, SONG_INSTRUMENT, SONG_SAMPLE

SAMPLE_ORDINAL: Final[int] = 0
PERSONS_HOLD_FRAMES: Final[int] = 10
PULSES: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.PULSE2)
EDIT_TITLE: Final[str] = "global.dialog.title.edit_voice_unsaved_reconstruction"
EDIT_MESSAGE: Final[str] = "global.dialog.message.edit_voice_unsaved_reconstruction"
SAVE: Final[str] = "global.dialog.label.save"
DISCARD: Final[str] = "global.dialog.label.discard"
CANCEL: Final[str] = "global.dialog.label.cancel"
REMOVE_VOICE: Final[str] = "sequencer.voices.label.context_remove"
FADING: Final[str] = "12 8 4"


def sample_title(screen: Screen, *, unsaved: bool) -> str:
    return voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=unsaved)


def leave_without_saving(screen: Screen) -> None:
    """Exits, letting the project's changes go at the question the exit asks."""
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()


def open_the_sample(screen: Screen) -> None:
    open_voice(screen, SONG_SAMPLE)

    screen.expect(screen.title, sample_title(screen, unsaved=False).__eq__, description="the sample open")
    assert screen.tabs.front() is Tab.RECONSTRUCTIONS


class TestAVoiceDoubleClickedOverAnEditedReconstruction:
    """A voice double-clicked while an edited reconstruction of its own stands open asks about the edits first."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_the_question_comes_first_and_cancel_keeps_the_reconstruction(self, screen: Screen) -> None:
        prompt = screen.reconstructions.unsaved_prompt
        edited = titled(screen, SONG.stem, marked(OPEN_RECONSTRUCTION.name, unsaved=True))
        stored: List[bytes] = []

        def edit_the_reconstruction(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            stored.append(OPEN_RECONSTRUCTION.read_bytes())

            raise_the_first_level(screen, ChannelName.PULSE1, title=edited)

        def the_double_click_asks_first(screen: Screen) -> None:
            double_click_voice(screen, SONG_SAMPLE)

            screen.expect(prompt.is_shown, bool, description="the question about unsaved changes")
            assert prompt.title() == screen.words(EDIT_TITLE)
            assert prompt.words() == screen.words(EDIT_MESSAGE)
            assert prompt.answers() == (screen.words(SAVE), screen.words(DISCARD), screen.words(CANCEL))
            assert screen.title() == edited

        def cancel_keeps_the_reconstruction(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert screen.title() == edited
            assert screen.reconstructions.shows_open(OPEN_RECONSTRUCTION)
            assert screen.tabs.front() is Tab.SEQUENCER

        def discard_opens_the_voice(screen: Screen) -> None:
            double_click_voice(screen, SONG_SAMPLE)
            screen.expect(prompt.is_shown, bool, description="the question again")

            prompt.confirm()

            screen.expect(screen.title, sample_title(screen, unsaved=False).__eq__, description="the sample open")
            assert screen.tabs.front() is Tab.RECONSTRUCTIONS
            assert OPEN_RECONSTRUCTION.read_bytes() == stored[0]

        screen.scenario(
            edit_the_reconstruction,
            the_double_click_asks_first,
            cancel_keeps_the_reconstruction,
            discard_opens_the_voice,
        ).run()


class TestTheOpenVoiceGoesWithItsProject:
    """The Reconstructions tab empties once the voice open on it leaves the project, or the project closes."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_removing_the_open_voice_empties_the_tab(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        menu = screen.context_menu

        def remove_it(screen: Screen) -> None:
            open_the_sample(screen)
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            voices.right_click(voice_row(screen, SONG_SAMPLE))
            screen.expect(menu.is_shown, bool, description="the voice's menu")

            menu.choose(screen.words(REMOVE_VOICE))

            screen.expect(voices.names, [SONG_INSTRUMENT].__eq__, description="the sample gone")
            assert not voices.remove_prompt.is_shown()

        def the_tab_empties(screen: Screen) -> None:
            screen.expect(
                screen.title,
                titled(screen, marked(SONG.stem, unsaved=True)).__eq__,
                description="nothing open beside the project",
            )
            assert screen.reconstructions.file_line() == ""

        screen.scenario(remove_it, the_tab_empties, leave_without_saving).run()

    def test_closing_the_project_empties_the_tab(self, screen: Screen) -> None:
        def close_the_project(screen: Screen) -> None:
            open_the_sample(screen)

            screen.project.close()

            screen.expect(screen.title, titled(screen).__eq__, description="nothing open")
            assert screen.reconstructions.file_line() == ""
            assert screen.sequencer.voices.names() == []

        screen.scenario(close_the_project).run()


class TestTheTabFollowsTheProjectsHistory:
    """Undo and redo pressed on the Sequencer tab redraw the voice open on the Reconstructions tab."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_undo_and_redo_of_a_sample_edit(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        drawn: Dict[str, str] = {}

        def edit_the_sample(screen: Screen) -> None:
            open_the_sample(screen)
            drawn["standing"] = reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME)

            drawn["edit"] = raise_the_first_level(screen, ChannelName.PULSE1, title=sample_title(screen, unsaved=True))

        def undo_from_the_sequencer(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            screen.press_shortcut(ShortcutId.UNDO)

            screen.expect(
                lambda: reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                drawn["standing"].__eq__,
                description="the edit undone",
            )

        def redo_from_the_sequencer(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.REDO)

            screen.expect(
                lambda: reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                drawn["edit"].__eq__,
                description="the edit redone",
            )
            assert screen.title() == sample_title(screen, unsaved=True)

        screen.scenario(edit_the_sample, undo_from_the_sequencer, redo_from_the_sequencer, leave_without_saving).run()

    def test_undo_of_an_instrument_edit_redraws_its_envelopes(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        drawn: Dict[str, str] = {}

        def edit_the_instrument(screen: Screen) -> None:
            open_voice(screen, SONG_INSTRUMENT)
            screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description="the instrument open")
            drawn["standing"] = reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME)

            edit_envelope(
                screen,
                channel=ChannelName.PULSE1,
                feature=FeatureKey.VOLUME,
                sequence=FADING,
                title=titled(screen, marked(SONG.stem, unsaved=True)),
            )

        def undo_from_the_sequencer(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            screen.press_shortcut(ShortcutId.UNDO)

            screen.expect(
                lambda: reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                drawn["standing"].__eq__,
                description="the edit undone",
            )
            assert screen.title() == titled(screen, SONG.stem)

        screen.scenario(edit_the_instrument, undo_from_the_sequencer).run()


class TestAVoiceOpenedByADoubleClickHeldAsAPersonHoldsIt:
    """A voice double-clicked opens as it stands, however long the second press is held."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a voice double-clicked with the second press held opens edited",
    )
    def test_the_voice_opens_unchanged(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        drawn: List[Tuple[str, ...]] = []

        def read_it_and_put_it_away(screen: Screen) -> None:
            open_the_sample(screen)
            drawn.append(tuple(reconstructions.envelope(channel, FeatureKey.VOLUME) for channel in PULSES))

            reconstructions.close_from_menu()

            screen.expect(screen.title, titled(screen, SONG.stem).__eq__, description="the sample put away")

        def double_click_it_holding_the_second_press(screen: Screen) -> None:
            screen.hand.double_click_held(voice_row(screen, SONG_SAMPLE), frames=PERSONS_HOLD_FRAMES)

            screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description="the sample in front")
            screen.frames(PERSONS_HOLD_FRAMES)
            assert screen.title() == sample_title(screen, unsaved=False)
            assert tuple(reconstructions.envelope(channel, FeatureKey.VOLUME) for channel in PULSES) == drawn[0]

        screen.scenario(read_it_and_put_it_away, double_click_it_holding_the_second_press).run()
