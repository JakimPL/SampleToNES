import multiprocessing
import operator
from pathlib import Path
from typing import Final, List

import pytest

from tests.screens.main.run.constants import BASS, RUN_TIMEOUT_SECONDS
from tests.screens.main.run.steps import written
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.vocabulary.converter import CANCEL_RUN, CONVERT_ONE

RUN_FAILED: Final[str] = "main.converter.message.status_error"


class TestAHeldRun:
    """A run shows its progress, Continue lets it run on, and Stop ends it with nothing written and every
    worker gone.

    A held run starts on one recording and the button turns to its cancel label. Pressing it asks about
    stopping; Cancel on that question keeps the run going. Pressing again and confirming ends the run,
    restores the Convert label and leaves no worker process and no written file.
    """

    @pytest.mark.usefixtures("conversion_hold")
    def test_progress_continue_and_stop(self, screen: Screen) -> None:
        converter = screen.main.converter
        prompt = converter.cancel_prompt
        destinations: List[Path] = []

        def start_it(screen: Screen) -> None:
            gather(screen, home_path(BASS))
            destinations.append(Path(converter.destination()))

            converter.press_action()

            screen.bridge.expect(
                converter.progress, lambda progress: progress > 0, description="progress", timeout=RUN_TIMEOUT_SECONDS
            )
            assert converter.action() == screen.words(CANCEL_RUN)

        def continue_lets_it_run(screen: Screen) -> None:
            converter.press_action()
            screen.expect(prompt.is_shown, bool, description="the question about stopping")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert converter.action() == screen.words(CANCEL_RUN)

        def stop_ends_it(screen: Screen) -> None:
            converter.press_action()
            screen.expect(prompt.is_shown, bool, description="the question again")

            prompt.confirm()

            screen.bridge.expect(
                converter.action,
                screen.words(CONVERT_ONE).format(name=home_path(BASS).stem).__eq__,
                description="the run over",
                timeout=RUN_TIMEOUT_SECONDS,
            )
            screen.bridge.expect(
                lambda: len(multiprocessing.active_children()),
                operator.not_,
                description="no worker left",
                timeout=RUN_TIMEOUT_SECONDS,
            )
            assert written(destinations[0]) == []

        screen.scenario(start_it, continue_lets_it_run, stop_ends_it).run()


class TestARecordingGoneBeforeTheRun:
    """A recording deleted after it was gathered is reported in words naming it when the run reaches it."""

    def test_the_run_says_what_went_wrong(self, screen: Screen) -> None:
        """An error notice opens with the run-failed words and the file's name, and the status line reads the
        run-failed words.
        """
        converter = screen.main.converter
        notice = screen.error_notice
        gather(screen, home_path(BASS))
        home_path(BASS).unlink()

        converter.press_action()

        screen.bridge.expect(notice.is_shown, bool, description="the failure reported", timeout=RUN_TIMEOUT_SECONDS)
        words = notice.words()
        screen.claim_error(home_path(BASS).name)
        notice.dismiss()
        screen.expect(notice.is_shown, operator.not_, description="the report dismissed")
        assert words.startswith(screen.words(RUN_FAILED))
        assert home_path(BASS).name in words
        assert converter.status() == screen.words(RUN_FAILED)
