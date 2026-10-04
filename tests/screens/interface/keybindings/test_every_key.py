import operator
from functools import partial
from typing import Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.keyboard import press_combination
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import channels_sounding, sounding_but
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT
from tests.suite.screens.written import written_application_config

TOGGLE_PULSE_TWO: Final[ShortcutId] = ShortcutId.TOGGLE_CHANNEL_PULSE_2
NEW_MAIN_KEY: Final[KeyCombination] = KeyCombination.parse("Ctrl+Shift+2")
KEY_LIST_SEPARATOR: Final[str] = ", "
SETTLING_FRAMES: Final[int] = 20


@pytest.fixture
def startup() -> Startup:
    """Opens the application with the arranged project and no reconstruction."""
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def written_out(combinations: List[KeyCombination]) -> str:
    return KEY_LIST_SEPARATOR.join(combination.display() for combination in combinations)


class TestEditingARowKeepsEveryKey:
    """A channel's row lists its main key and its chord, and a new main key keeps both.

    The Pulse 2 row shows every key the scheme gives it. A pressed key leads the list and the earlier keys
    follow it. After OK the chord still mutes Pulse 2, the new key brings it back, and leaving writes every
    key down.
    """

    def test_the_row_keeps_its_second_key(self, screen: Screen) -> None:
        settings = screen.keyboard_settings
        shipped: List[KeyCombination] = []

        def the_row_shows_every_key(screen: Screen) -> None:
            shipped.extend(screen.shortcut(TOGGLE_PULSE_TWO).combinations())
            settings.open()
            screen.expect(settings.is_shown, bool, description="Keyboard settings")

            assert len(shipped) > 1
            assert settings.keys_of(TOGGLE_PULSE_TWO) == written_out(shipped)

        def a_pressed_key_leads_the_others(screen: Screen) -> None:
            settings.listen_for(TOGGLE_PULSE_TWO)

            press_combination(screen.hand, NEW_MAIN_KEY)

            screen.expect(
                partial(settings.keys_of, TOGGLE_PULSE_TWO),
                written_out([NEW_MAIN_KEY, *shipped]).__eq__,
                description="the new key ahead of the others",
            )
            settings.confirm()
            screen.expect(settings.is_shown, operator.not_, description="Keyboard settings closed")

        def the_chord_still_mutes_pulse_two(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            screen.frames(SETTLING_FRAMES)

            press_combination(screen.hand, shipped[-1])

            screen.expect(
                partial(channels_sounding, screen),
                sounding_but(ChannelName.PULSE2).__eq__,
                description="Pulse 2 muted",
            )

        def the_new_key_brings_it_back(screen: Screen) -> None:
            press_combination(screen.hand, NEW_MAIN_KEY)

            screen.expect(
                partial(channels_sounding, screen),
                sounding_but().__eq__,
                description="every channel sounding again",
            )

        def leaving_writes_every_key(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()
            assert written_application_config().shortcuts.overrides == {
                TOGGLE_PULSE_TWO.value: written_out([NEW_MAIN_KEY, *shipped]),
            }

        screen.scenario(
            the_row_shows_every_key,
            a_pressed_key_leads_the_others,
            the_chord_still_mutes_pulse_two,
            the_new_key_brings_it_back,
            leaving_writes_every_key,
        ).run()
