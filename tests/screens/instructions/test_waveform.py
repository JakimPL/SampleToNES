from functools import partial
from typing import Final

from sampletones_application.tags.general import TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY
from sampletones_core.constants.enums import GeneratorName
from tests.suite.screens.dearpygui.items import read_label
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.instructions import load_library
from tests.suite.screens.world import one_worker_config

LISTENING_FRAMES: Final[int] = 30
ZOOM_NOTCHES: Final[int] = 3
PAUSE: Final[str] = "global.menu.label.item_playback_pause"


def show_the_pulse(screen: Screen) -> None:
    instructions = screen.instructions
    tree = instructions.library.tree
    load_library(screen, one_worker_config())
    row = screen.expect_item(partial(tree.generator_row, GeneratorName.PULSE), description="the pulse row")

    tree.click(row)

    screen.expect(instructions.waveform.series, bool, description="the pulse drawn")


class TestTheFragmentWaveform:
    """A click on the fragment's waveform sounds it, and a drag across a narrowed view sounds nothing.

    A fragment lasts a few frames, so what plays is read on every frame the gesture spans.
    """

    def test_a_click_sounds_it_and_a_drag_does_not(self, screen: Screen) -> None:
        waveform = screen.instructions.waveform
        playing = screen.words(PAUSE)

        def a_drag_sounds_nothing(screen: Screen) -> None:
            show_the_pulse(screen)
            waveform.zoom_in(0.5, ZOOM_NOTCHES)

            with screen.record(partial(read_label, TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY)) as recording:
                waveform.drag(0.6, 0.4)
                screen.frames(LISTENING_FRAMES)

            assert playing not in recording.values()

        def a_click_sounds_it(screen: Screen) -> None:
            with screen.record(partial(read_label, TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY)) as recording:
                waveform.click(0.5)
                screen.frames(LISTENING_FRAMES)

            assert playing in recording.values()

        screen.scenario(a_drag_sounds_nothing, a_click_sounds_it).run()
