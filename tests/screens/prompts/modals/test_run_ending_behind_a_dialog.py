import operator
from typing import Dict, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.prompts.modals.constants import SETTLING_FRAMES
from tests.suite.screens.holds.conversion import ConversionHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import RUN_TIMEOUT_SECONDS, gather, home_path
from tests.suite.screens.vocabulary.converter import CONVERT_ONE
from tests.suite.screens.vocabulary.settings import LISTENING
from tests.suite.screens.worlds.recordings import BASS


def start_a_held_run(screen: Screen) -> None:
    """Converts the home's bass on the Main tab; the hold keeps the run halfway and the function returns once
    progress shows.
    """
    converter = screen.main.converter
    screen.tabs.bring_to_front(Tab.MAIN)
    gather(screen, home_path(BASS))

    converter.press_action()

    screen.bridge.expect(
        converter.progress, lambda progress: progress > 0, description="progress", timeout=RUN_TIMEOUT_SECONDS
    )


def let_the_run_end(screen: Screen, hold: ConversionHold) -> None:
    """Releases the held run and waits until it is over, while its question waits for its turn."""
    converter = screen.main.converter
    hold.release()

    screen.bridge.expect(
        converter.action,
        screen.words(CONVERT_ONE).format(name=home_path(BASS).stem).__eq__,
        description="the run over",
        timeout=RUN_TIMEOUT_SECONDS,
    )
    screen.frames(SETTLING_FRAMES)


def the_end_comes_and_closes(screen: Screen) -> None:
    """Expects the run's question to come once the screen is free, and Cancel puts it away."""
    end = screen.main.converter.end_prompt
    screen.expect(end.is_shown, bool, description="the run's question")
    assert len(screen.shown_windows()) == 1

    end.cancel()

    screen.expect(end.is_shown, operator.not_, description="the run's question answered")
    assert screen.shown_windows() == ()


class TestARunEndingBehindDisplaySettings:
    """A run that ends while Display settings is open asks its question once the dialog is answered."""

    def test_the_question_waits_for_an_unchanged_dialog(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        """With Display settings left unchanged, the run's question comes after Cancel closes the dialog."""
        settings = screen.display_settings

        def open_display_settings_over_a_held_run(screen: Screen) -> None:
            start_a_held_run(screen)

            settings.open()

            screen.expect(settings.is_shown, bool, description="Display settings")

        def the_run_ends_and_its_question_waits(screen: Screen) -> None:
            let_the_run_end(screen, conversion_hold)

            assert settings.is_shown()
            assert not screen.main.converter.end_prompt.is_shown()

        def cancel_hands_the_screen_over(screen: Screen) -> None:
            settings.cancel()

            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")
            the_end_comes_and_closes(screen)

        screen.scenario(
            open_display_settings_over_a_held_run,
            the_run_ends_and_its_question_waits,
            cancel_hands_the_screen_over,
        ).run()

    def test_the_discard_question_comes_before_the_runs(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        """With a changed setting, Cancel asks about discarding the change first, and the run's question comes
        after Discard.
        """
        settings = screen.display_settings
        discard = settings.discard_prompt

        def change_display_settings_over_a_held_run(screen: Screen) -> None:
            start_a_held_run(screen)
            settings.open()
            screen.expect(settings.is_shown, bool, description="Display settings")
            original = settings.vsync()

            settings.toggle_vsync()

            screen.expect(settings.vsync, original.__ne__, description="the box flipped")

        def the_run_ends_and_its_question_waits(screen: Screen) -> None:
            let_the_run_end(screen, conversion_hold)

            assert settings.is_shown()
            assert not screen.main.converter.end_prompt.is_shown()

        def cancel_asks_about_the_change_first(screen: Screen) -> None:
            settings.cancel()

            screen.expect(discard.is_shown, bool, description="the discard question")
            screen.frames(SETTLING_FRAMES)
            assert not screen.main.converter.end_prompt.is_shown()
            assert len(screen.shown_windows()) == 1

        def discard_hands_the_screen_over(screen: Screen) -> None:
            discard.confirm()

            screen.expect(discard.is_shown, operator.not_, description="the discard question answered")
            assert not settings.is_shown()
            the_end_comes_and_closes(screen)

        screen.scenario(
            change_display_settings_over_a_held_run,
            the_run_ends_and_its_question_waits,
            cancel_asks_about_the_change_first,
            discard_hands_the_screen_over,
        ).run()


class TestARunEndingBehindTheWindowModeCountdown:
    """A run that ends while the window-mode countdown shows waits for the countdown and for the dialog behind
    it.
    """

    def test_the_question_waits_for_keep_and_the_dialog(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        """Keep brings the dialog back, and the run's question comes after the change is discarded."""
        settings = screen.display_settings
        discard = settings.discard_prompt
        original: List[bool] = []

        def change_the_window_mode_over_a_held_run(screen: Screen) -> None:
            start_a_held_run(screen)
            settings.open()
            screen.expect(settings.is_shown, bool, description="Display settings")
            original.append(settings.borderless())

            settings.toggle_borderless()

            screen.expect(settings.countdown_shown, bool, description="the countdown")
            assert not settings.is_shown()

        def the_run_ends_and_its_question_waits(screen: Screen) -> None:
            let_the_run_end(screen, conversion_hold)

            assert settings.countdown_shown()
            assert not screen.main.converter.end_prompt.is_shown()

        def keep_brings_the_dialog_back_first(screen: Screen) -> None:
            settings.keep()

            screen.expect(settings.is_shown, bool, description="Display settings back")
            screen.frames(SETTLING_FRAMES)
            assert not settings.countdown_shown()
            assert not screen.main.converter.end_prompt.is_shown()
            assert settings.borderless() != original[0]

        def discarding_the_change_hands_the_screen_over(screen: Screen) -> None:
            settings.cancel()
            screen.expect(discard.is_shown, bool, description="the discard question")

            discard.confirm()

            screen.expect(discard.is_shown, operator.not_, description="the discard question answered")
            the_end_comes_and_closes(screen)

        screen.scenario(
            change_the_window_mode_over_a_held_run,
            the_run_ends_and_its_question_waits,
            keep_brings_the_dialog_back_first,
            discarding_the_change_hands_the_screen_over,
        ).run()


class TestARunEndingBehindTheReassignQuestion:
    """A run that ends while Keyboard settings asks to reassign keys waits for the question and for the dialog
    behind it.
    """

    def test_the_question_waits_for_both(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        """Cancel brings the dialog back, and the run's question comes after the dialog closes."""
        settings = screen.keyboard_settings
        reassign = settings.reassign_prompt
        keys: Dict[ShortcutId, str] = {}

        def ask_to_reassign_over_a_held_run(screen: Screen) -> None:
            start_a_held_run(screen)
            settings.open()
            screen.expect(settings.is_shown, bool, description="Keyboard settings")
            keys.update(
                {shortcut_id: settings.keys_of(shortcut_id) for shortcut_id in (ShortcutId.UNDO, ShortcutId.REDO)}
            )
            settings.listen_for(ShortcutId.REDO)

            screen.press_shortcut(ShortcutId.UNDO)

            screen.expect(reassign.is_shown, bool, description="the question about reassigning")
            assert not settings.is_shown()

        def the_run_ends_and_its_question_waits(screen: Screen) -> None:
            let_the_run_end(screen, conversion_hold)

            assert reassign.is_shown()
            assert not screen.main.converter.end_prompt.is_shown()

        def cancel_brings_the_dialog_back_first(screen: Screen) -> None:
            reassign.cancel()

            screen.expect(settings.is_shown, bool, description="Keyboard settings back")
            screen.frames(SETTLING_FRAMES)
            assert not screen.main.converter.end_prompt.is_shown()
            assert settings.keys_of(ShortcutId.UNDO) == keys[ShortcutId.UNDO]

        def closing_the_dialog_hands_the_screen_over(screen: Screen) -> None:
            settings.cancel()

            screen.expect(settings.is_shown, operator.not_, description="Keyboard settings closed")
            the_end_comes_and_closes(screen)

        screen.scenario(
            ask_to_reassign_over_a_held_run,
            the_run_ends_and_its_question_waits,
            cancel_brings_the_dialog_back_first,
            closing_the_dialog_hands_the_screen_over,
        ).run()


class TestTheRowListeningAfterTheReassignQuestion:
    """A row that reads as listening after Cancel answers the reassign question takes the next keys pressed.

    Redo listens, Undo's keys ask to reassign, and Cancel brings the dialog back with the row still
    listening. The same keys then ask again.
    """

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a row listening again after the reassign question takes no keys",
    )
    def test_the_same_keys_ask_again(self, screen: Screen) -> None:
        """The same keys pressed again ask the reassign question once more."""
        settings = screen.keyboard_settings
        reassign = settings.reassign_prompt
        settings.open()
        screen.expect(settings.is_shown, bool, description="Keyboard settings")
        settings.listen_for(ShortcutId.REDO)
        screen.press_shortcut(ShortcutId.UNDO)
        screen.expect(reassign.is_shown, bool, description="the question about reassigning")
        reassign.cancel()
        screen.expect(settings.is_shown, bool, description="Keyboard settings back")
        assert settings.keys_of(ShortcutId.REDO) == screen.words(LISTENING)

        screen.press_shortcut(ShortcutId.UNDO)

        screen.expect(reassign.is_shown, bool, description="the question about reassigning again")
