from functools import partial
from typing import Callable, Dict, List, Optional

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.constants.enums import GeneratorName
from tests.screens.reconstructions.instruments.constants import NOTE_FRAMES, PIANO_C
from tests.screens.reconstructions.instruments.steps import give_it_a_volume
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import leave_letting_the_project_go
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.views.waveform import read_cursor
from tests.suite.screens.vocabulary.playback import PLAY
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION, SONG, SONG_INSTRUMENT


class TestTheAuditionSwitch:
    """The Audition switch draws the instrument on the generator it names, and back.

    The instrument gets a volume and shows on the pulse. Choosing the triangle redraws the waveform,
    choosing the pulse again restores the first drawing, and the application exits letting the project
    go.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_each_generator_redraws_the_waveform(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        waveform = screen.reconstructions.waveform
        drawn: Dict[GeneratorName, List[float]] = {}

        def drawn_now() -> List[float]:
            return waveform.drawn(SONG_INSTRUMENT)

        def on_the_pulse(screen: Screen) -> None:
            give_it_a_volume(screen)

            assert instruments.audition() == screen.generator_words(GeneratorName.PULSE)
            drawn[GeneratorName.PULSE] = drawn_now()

        def on_the_triangle(screen: Screen) -> None:
            instruments.choose_audition(screen.generator_words(GeneratorName.TRIANGLE))

            drawn[GeneratorName.TRIANGLE] = screen.expect(
                drawn_now, drawn[GeneratorName.PULSE].__ne__, description="the waveform redrawn"
            )

        def back_on_the_pulse(screen: Screen) -> None:
            instruments.choose_audition(screen.generator_words(GeneratorName.PULSE))

            screen.expect(drawn_now, drawn[GeneratorName.PULSE].__eq__, description="the pulse drawn again")

        screen.scenario(on_the_pulse, on_the_triangle, back_on_the_pulse, leave_letting_the_project_go).run()


class TestAnInstrumentsWaveform:
    """A click on an open instrument's waveform keeps playback silent, while a note key sounds it.

    A reconstruction that plays stands open before the instrument, so any sound from a click is heard as
    a moving cursor. The click leaves the cursor still and the Play button as it was; the note key moves
    the cursor.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song and a playable reconstruction."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=SONG)

    def test_a_click_plays_nothing_and_a_key_does(self, screen: Screen) -> None:
        waveform = screen.reconstructions.waveform

        def cursors_over(gesture: Callable[[], None]) -> List[Optional[float]]:
            with screen.record(partial(read_cursor, waveform.cursor_line)) as recording:
                gesture()
                screen.frames(NOTE_FRAMES)

            return recording.values()

        def a_click_plays_nothing(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            give_it_a_volume(screen)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            cursors = cursors_over(partial(waveform.click, 0.5))

            assert not any(cursors)
            assert screen.sequencer.playback.play_entry() == screen.words(PLAY)

        def a_note_key_sounds_it(screen: Screen) -> None:
            cursors = cursors_over(partial(screen.hand.press_key, PIANO_C, modifiers=[]))

            assert any(cursors)

        screen.scenario(a_click_plays_nothing, a_note_key_sounds_it, leave_letting_the_project_go).run()
