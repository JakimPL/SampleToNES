import operator
import stat
from typing import Dict, Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.holds import ConversionHold, RegenerationHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import RUN_TIMEOUT_SECONDS, gather, home_path
from tests.suite.screens.steps.reconstructions import (
    expect_open,
    load_from_the_browser,
    marked,
    raise_the_first_level_while_held,
    remove_from_the_browser,
    titled,
)
from tests.suite.screens.world import BASS, OPEN_RECONSTRUCTION, OTHER_RECONSTRUCTION

SETTLING_FRAMES: Final[int] = 30
KEPT: Final[str] = "Kept.stn"
LOCKED_FOLDER: Final[str] = "Locked"
READ_AND_ENTER: Final[int] = stat.S_IRUSR | stat.S_IXUSR
CONVERT_ONE: Final[str] = "main.converter.template.convert_recording"
LOAD_TITLE: Final[str] = "global.dialog.title.load_unsaved_reconstruction"
CLOSE_TITLE: Final[str] = "global.dialog.title.close_unsaved_reconstruction"
SAVE_FAILED: Final[str] = "global.dialog.message.reconstruction_save_failed"
REBUILD_FAILURE: Final[str] = "The rebuild broke on its worker"
LISTENING: Final[str] = "settings.keybindings.message.capturing"


class RebuildBrokeError(RuntimeError):
    """The failure a held rebuild is let go as, standing for a rebuild that raised."""


def start_a_held_run(screen: Screen) -> None:
    """Converts the home's bass, which the hold keeps running halfway."""
    converter = screen.main.converter
    screen.tabs.bring_to_front(Tab.MAIN)
    gather(screen, home_path(BASS))

    converter.press_action()

    screen.bridge.expect(
        converter.progress, lambda progress: progress > 0, description="progress", timeout=RUN_TIMEOUT_SECONDS
    )


def let_the_run_end(screen: Screen, hold: ConversionHold) -> None:
    """Lets the held run go, and waits for it to be over while its question waits its turn."""
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
    """The run's question comes once the screen is free, and Close puts it away."""
    end = screen.main.converter.end_prompt
    screen.expect(end.is_shown, bool, description="the run's question")
    assert len(screen.shown_windows()) == 1

    end.cancel()

    screen.expect(end.is_shown, operator.not_, description="the run's question answered")
    assert screen.shown_windows() == ()


class TestARunEndingBehindDisplaySettings:
    """A run that ends while Display settings stands asks its question once the dialog is answered."""

    def test_the_question_waits_for_an_unchanged_dialog(self, screen: Screen, conversion_hold: ConversionHold) -> None:
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
    """A run that ends while the window-mode countdown stands waits for the countdown and the dialog behind it."""

    def test_the_question_waits_for_keep_and_the_dialog(self, screen: Screen, conversion_hold: ConversionHold) -> None:
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
    """A run that ends while Keyboard settings asks to reassign keys waits for the question and the dialog behind it."""

    def test_the_question_waits_for_both(self, screen: Screen, conversion_hold: ConversionHold) -> None:
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
    """A row that reads as listening once Cancel answers the reassign question takes the next keys pressed."""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a row listening again after the reassign question takes no keys",
    )
    def test_the_same_keys_ask_again(self, screen: Screen) -> None:
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


class TestTwoGesturesWaitingOnAHeldRebuild:
    """A load and a close asked for while an edit is on its way each ask their question once it lands, in order."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_their_questions_come_one_after_the_other(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        typed: List[str] = []

        def edit_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            typed.append(raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1))

        def load_and_close_while_it_is_held(screen: Screen) -> None:
            load_from_the_browser(screen, OTHER_RECONSTRUCTION)
            reconstructions.close_from_menu()

            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert reconstructions.shows_open(OPEN_RECONSTRUCTION)

        def the_load_asks_first(screen: Screen) -> None:
            regeneration_hold.release()

            screen.expect(prompt.is_shown, bool, description="the first question")
            assert prompt.title() == screen.words(LOAD_TITLE)
            assert len(screen.shown_windows()) == 1

        def the_close_asks_next(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.title, screen.words(CLOSE_TITLE).__eq__, description="the second question")
            assert len(screen.shown_windows()) == 1

        def nothing_asks_after_them(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the questions answered")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.title() == titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True))
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == typed[0]

        def leave_letting_it_go(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(prompt.is_shown, bool, description="the question about leaving")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(
            edit_while_the_rebuild_is_held,
            load_and_close_while_it_is_held,
            the_load_asks_first,
            the_close_asks_next,
            nothing_asks_after_them,
            leave_letting_it_go,
        ).run()


class TestAFailedRebuildBeforeAClose:
    """A rebuild that fails while a close waits on it reports the failure first, and the close asks after."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_the_failure_first_and_the_question_after(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        notice = screen.error_notice
        standing: List[str] = []

        def edit_a_removed_reconstruction_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            remove_from_the_browser(screen, OPEN_RECONSTRUCTION)
            screen.expect(
                screen.title,
                titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True)).__eq__,
                description="the reconstruction left unsaved",
            )
            standing.append(reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME))

            raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1)

        def close_while_it_is_held(screen: Screen) -> None:
            reconstructions.close_from_menu()

            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()

        def the_failure_comes_first(screen: Screen) -> None:
            regeneration_hold.fail(RebuildBrokeError(REBUILD_FAILURE))

            screen.expect(notice.is_shown, bool, description="the failure reported")
            screen.claim_error(RebuildBrokeError.__name__)
            screen.frames(SETTLING_FRAMES)
            assert not prompt.is_shown()
            assert len(screen.shown_windows()) == 1

        def the_question_comes_once_the_failure_is_read(screen: Screen) -> None:
            notice.dismiss()

            screen.expect(prompt.is_shown, bool, description="the question about closing")
            assert prompt.title() == screen.words(CLOSE_TITLE)

        def cancel_keeps_the_reconstruction_as_it_stood(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question answered")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == standing[0]

        def leave_letting_it_go(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(prompt.is_shown, bool, description="the question about leaving")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(
            edit_a_removed_reconstruction_while_the_rebuild_is_held,
            close_while_it_is_held,
            the_failure_comes_first,
            the_question_comes_once_the_failure_is_read,
            cancel_keeps_the_reconstruction_as_it_stood,
            leave_letting_it_go,
        ).run()


class TestASaveIntoAFolderThatTakesNothing:
    """A save into a folder that takes no file shows its failure alone, and the reconstruction stays open."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_the_failure_stands_alone_and_a_save_elsewhere_closes_it(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        notice = screen.error_notice
        locked = RECONSTRUCTIONS_DIRECTORY / LOCKED_FOLDER
        kept = RECONSTRUCTIONS_DIRECTORY / KEPT

        def remove_its_file(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            locked.mkdir()
            locked.chmod(READ_AND_ENTER)

            remove_from_the_browser(screen, OPEN_RECONSTRUCTION)

            screen.expect(
                screen.title,
                titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True)).__eq__,
                description="the reconstruction left unsaved",
            )

        def save_into_the_locked_folder(screen: Screen) -> None:
            reconstructions.close_from_menu()
            screen.expect(prompt.is_shown, bool, description="the question about closing")
            screen.answer_next_dialog(DialogKind.SAVE, locked / KEPT)

            prompt.save()

            screen.expect(notice.is_shown, bool, description="the failure reported")
            screen.claim_error(PermissionError.__name__)
            assert screen.words(SAVE_FAILED) in notice.words()
            screen.frames(SETTLING_FRAMES)
            assert not prompt.is_shown()
            assert len(screen.shown_windows()) == 1

        def dismissing_it_leaves_the_reconstruction_open(screen: Screen) -> None:
            notice.dismiss()

            screen.expect(notice.is_shown, operator.not_, description="the failure dismissed")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.title() == titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True))
            assert not (locked / KEPT).exists()

        def a_save_elsewhere_closes_it(screen: Screen) -> None:
            reconstructions.close_from_menu()
            screen.expect(prompt.is_shown, bool, description="the question again")
            screen.answer_next_dialog(DialogKind.SAVE, kept)

            prompt.save()

            screen.expect(screen.title, titled(screen).__eq__, description="the reconstruction closed")
            assert kept.exists()

        screen.scenario(
            remove_its_file,
            save_into_the_locked_folder,
            dismissing_it_leaves_the_reconstruction_open,
            a_save_elsewhere_closes_it,
        ).run()
