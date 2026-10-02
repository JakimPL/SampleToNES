import operator
import re
from functools import partial
from typing import Final, List, Tuple

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.sequencer import TAG_SEQUENCER_VOICES_TABLE
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.items import Item, enclosing_regions, read_region_view
from tests.suite.screens.keyboard import press_combination
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import BY_CONFIGURATION
from tests.suite.screens.views.menus import MenuEntry
from tests.suite.screens.world import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD, SHORT_RECONSTRUCTION

POOL_ACTIONS: Final[Tuple[str, ...]] = (
    "sequencer.voices.label.new_instrument",
    "sequencer.voices.label.add_sample",
    "sequencer.voices.label.import_instrument",
)
PLAY_VOICE: Final[str] = "global.context.label.play"
STATUS_SAMPLE: Final[str] = "sequencer.voices.template.status_sample"
STATUS_SEPARATOR: Final[str] = "sequencer.voices.template.status_channel_separator"
LINE_CHANNEL_NAMES: Final[Tuple[str, ...]] = (
    "global.context.label.pulse_1",
    "global.context.label.triangle",
    "global.context.label.noise",
)
PAUSE: Final[str] = "global.menu.label.item_playback_pause"
EMPTY_SPACE_INSET: Final[int] = 10
SETTLING_FRAMES: Final[int] = 20
MOVE_DOWN_KEYS: Final[str] = "Alt+Down"
PLACED_ROW: Final[int] = 1
ADDED_NUMBER: Final[str] = "03"
HOVER_RACE: Final[str] = "Error executing callback _on_row_hovered"


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def voice_row(screen: Screen, name: str) -> Item:
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    return screen.expect_item(partial(screen.sequencer.voices.row, name), description=f"the row of {name}")


def right_click_the_empty_list(screen: Screen) -> None:
    """Presses the right button over the list below its rows."""
    view = screen.bridge.ask(lambda: read_region_view(enclosing_regions(TAG_SEQUENCER_VOICES_TABLE)[0]))
    assert view is not None
    screen.hand.right_click_at(
        Point(x=round(view.x + view.width / 2), y=round(view.y + view.height - EMPTY_SPACE_INSET))
    )


def voice_actions(entries: List[str], pool: Tuple[str, ...]) -> List[str]:
    """The entries acting on the voice picked, which leaves out the pool's own."""
    return [entry for entry in entries if entry not in pool]


def menu_on_the_bar(screen: Screen, group: MenuElements) -> List[MenuEntry]:
    """Opens the menu ``group`` with a click, reads what it offers once it settles, and puts it away."""
    screen.menu.open(group)
    screen.frames(SETTLING_FRAMES)
    entries = screen.menu.entries(group)
    screen.menu.close()
    screen.frames(SETTLING_FRAMES)
    return entries


def forgive_the_hover_race(screen: Screen) -> None:
    """Forgives the error a voice row's hover meets once the list has rebuilt the row, which the ledger records."""
    screen.forgive_known_error(HOVER_RACE)


def leave_letting_the_project_go(screen: Screen) -> None:
    forgive_the_hover_race(screen)
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()


class TestTheVoicesMenus:
    """A voice row's menu offers the voice's actions and the pool's; the empty list offers the pool's alone.

    The Voice and Edit menus name the voice's actions the row's menu names, Play aside, and the keys
    they print are the keys that fire them.
    """

    def test_menus_agree_and_their_keys_fire(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        menu = screen.context_menu
        pool = tuple(screen.words(key) for key in POOL_ACTIONS)
        row_actions: List[str] = []

        def the_row_offers_both(screen: Screen) -> None:
            voices.right_click(voice_row(screen, LINE))
            screen.expect(menu.is_shown, bool, description="the row's menu")
            labels = menu.labels()
            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")

            assert tuple(labels[-len(pool) :]) == pool
            row_actions.extend(voice_actions(labels, pool))

        def the_empty_list_offers_the_pool_alone(screen: Screen) -> None:
            right_click_the_empty_list(screen)

            screen.expect(menu.is_shown, bool, description="the list's menu")
            labels = menu.labels()
            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")
            assert tuple(labels) == pool

        def the_bar_menus_name_the_same_actions(screen: Screen) -> None:
            voices.pick(voice_row(screen, LINE))
            screen.expect(partial(voices.is_picked, 0), bool, description="the line picked")

            voice_menu = menu_on_the_bar(screen, MenuElements.GROUP_VOICE)
            edit_menu = menu_on_the_bar(screen, MenuElements.GROUP_EDIT)

            from_voice = [entry for entry in voice_menu if entry.label in row_actions]
            from_edit = [entry for entry in edit_menu if entry.label in row_actions]
            assert [entry.label for entry in from_voice] == [entry.label for entry in from_edit]
            assert [entry.keys for entry in from_voice] == [entry.keys for entry in from_edit]
            assert set(row_actions) - {entry.label for entry in from_voice} == {screen.words(PLAY_VOICE)}

        def the_printed_keys_fire(screen: Screen) -> None:
            moves = [
                entry for entry in menu_on_the_bar(screen, MenuElements.GROUP_VOICE) if entry.keys == MOVE_DOWN_KEYS
            ]
            assert moves

            press_combination(screen.hand, KeyCombination.parse(moves[0].keys))

            screen.expect(voices.names, [BASS_VOICE, LINE, PAD].__eq__, description="the line moved down")

        screen.scenario(
            the_row_offers_both,
            the_empty_list_offers_the_pool_alone,
            the_bar_menus_name_the_same_actions,
            the_printed_keys_fire,
            leave_letting_the_project_go,
        ).run()


class TestHoveringAVoice:
    """The status line says what the voice under the pointer is: its name, its kind and the channels it plays."""

    def test_the_status_names_the_sample(self, screen: Screen) -> None:
        row = voice_row(screen, LINE)
        separator = screen.words(STATUS_SEPARATOR)
        channels = separator.join(screen.words(key) for key in LINE_CHANNEL_NAMES)
        template = screen.words(STATUS_SAMPLE).format(name=LINE, channels=channels, bytes="{bytes}")
        expected = re.compile(re.escape(template).replace(re.escape("{bytes}"), ".+"))

        screen.hand.move_to(Point(x=0, y=0))
        screen.hand.hover(row)

        screen.expect(screen.status, lambda status: expected.fullmatch(status) is not None, description="the status")
        forgive_the_hover_race(screen)


class TestTheKeysOfACollapsedVoicesCard:
    """With the Voices card collapsed, the keys of the voice picked change nothing; open, they act."""

    def test_keys_wait_for_the_card(self, screen: Screen) -> None:
        voices = screen.sequencer.voices

        def pick_the_line_and_collapse_the_card(screen: Screen) -> None:
            voices.pick(voice_row(screen, LINE))
            screen.expect(partial(voices.is_picked, 0), bool, description="the line picked")

            voices.card.toggle()

            screen.expect(voices.card.is_collapsed, bool, description="the card collapsed")

        def its_keys_change_nothing(screen: Screen) -> None:
            press_combination(screen.hand, KeyCombination.parse(MOVE_DOWN_KEYS))
            screen.press_shortcut(ShortcutId.VOICES_REMOVE_VOICE)

            screen.frames(SETTLING_FRAMES)
            assert voices.names() == [LINE, BASS_VOICE, PAD]
            assert screen.shown_windows() == ()

        def open_they_act(screen: Screen) -> None:
            voices.card.toggle()
            screen.expect(voices.card.is_collapsed, operator.not_, description="the card open")
            voices.pick(voice_row(screen, LINE))

            press_combination(screen.hand, KeyCombination.parse(MOVE_DOWN_KEYS))

            screen.expect(voices.names, [BASS_VOICE, LINE, PAD].__eq__, description="the line moved down")

        screen.scenario(
            pick_the_line_and_collapse_the_card,
            its_keys_change_nothing,
            open_they_act,
            leave_letting_the_project_go,
        ).run()


class TestNewInstrumentWithNoProjectOpen:
    """New instrument with no project open adds nothing, and leaving asks nothing."""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: New instrument with no project open writes into a project nobody opened",
    )
    def test_nothing_is_added(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        screen.tabs.bring_to_front(Tab.SEQUENCER)
        screen.project.close()
        screen.expect(voices.names, operator.not_, description="no voices listed")

        voices.new_instrument()

        screen.frames(SETTLING_FRAMES)
        assert voices.names() == []
        screen.press_shortcut(ShortcutId.EXIT)
        assert screen.wait_for_exit()


class TestASampleAddedFromTheBrowser:
    """A reconstruction double-clicked in the Sequencer's browser joins the voices; placed, the song plays it."""

    def test_it_joins_and_plays(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        browser = screen.sequencer.browser
        tracker = screen.sequencer.tracker

        def double_click_it_in_the_browser(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            heading = screen.expect_item(
                partial(browser.heading, screen.words(BY_CONFIGURATION)), description="the heading"
            )
            if not browser.is_open(heading):
                browser.open_by_click(heading)
            row = screen.expect_item(partial(browser.file_row, SHORT_RECONSTRUCTION), description="its row")

            browser.double_click(row)

            screen.expect(lambda: len(voices.names()), (4).__eq__, description="a fourth voice")
            assert voices.names()[:3] == [LINE, BASS_VOICE, PAD]

        def placed_the_song_plays_it(screen: Screen) -> None:
            tracker.click(PLACED_ROW, ChannelName.PULSE2, SubColumn.VOICE)
            screen.hand.type_text(ADDED_NUMBER)
            screen.expect(
                partial(tracker.label, PLACED_ROW, ChannelName.PULSE2, SubColumn.VOICE),
                ADDED_NUMBER.__eq__,
                description="the sample placed",
            )

            screen.press_shortcut(ShortcutId.PLAY)

            screen.expect(screen.sequencer.playback.play_entry, screen.words(PAUSE).__eq__, description="playing")
            screen.press_shortcut(ShortcutId.STOP)

        screen.scenario(double_click_it_in_the_browser, placed_the_song_plays_it, leave_letting_the_project_go).run()
