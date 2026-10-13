import operator
from pathlib import Path
from typing import Final, List

import pytest

from automation.screen import Screen
from automation.steps.main import gather, home_path
from automation.worlds.home import World
from tests.screens.main.run.conftest import recording
from tests.screens.main.run.constants import RUN_TIMEOUT_SECONDS
from tests.screens.main.run.steps import written
from tests.suite.screens.seeds.recordings import UnreadableRecording
from tests.suite.screens.worlds.recordings import converting_world

TAKES: Final[str] = "Takes"
BROKEN_TAKES: Final[str] = "Broken"
FIRST: Final[str] = "first.wav"
SECOND: Final[str] = "second.wav"
BROKEN: Final[str] = "broken.wav"
DAMAGED: Final[str] = "damaged.wav"
SKIPPED_ONE: Final[str] = "main.converter.message.skipped_recording_heading"
SKIPPED_SEVERAL: Final[str] = "main.converter.template.skipped_recordings_heading"
NOTHING_WRITTEN: Final[str] = "main.converter.message.nothing_written"


class TestABatchGoesOnPastABrokenRecording:
    """A folder holding a recording no reader takes converts the rest, and the end names the one it skipped.

    The folder is gathered and converted. The end of the run offers what it wrote and lists the broken
    recording under its heading. The reconstructions of the readable recordings are written, and the
    broken one has none.
    """

    @pytest.fixture
    def world(self) -> World:
        folder = home_path(TAKES)
        return converting_world(
            (
                recording(folder / FIRST),
                UnreadableRecording(destination=folder / BROKEN),
                recording(folder / SECOND),
            )
        )

    def test_the_rest_is_written_and_the_end_names_the_broken_one(self, screen: Screen) -> None:
        converter = screen.main.converter
        destinations: List[Path] = []

        def convert(screen: Screen) -> None:
            gather(screen, home_path(TAKES))
            destinations.append(Path(converter.destination()))

            converter.press_action()

            screen.claim_error(BROKEN)
            screen.bridge.expect(
                converter.end_prompt.is_shown,
                bool,
                description="the run's end",
                timeout=RUN_TIMEOUT_SECONDS,
            )

        def the_end_names_it(screen: Screen) -> None:
            words = converter.end_prompt.words()
            converter.end_prompt.cancel()
            screen.expect(converter.end_prompt.is_shown, operator.not_, description="the end closed")

            assert screen.words(SKIPPED_ONE) in words
            assert BROKEN in words
            assert FIRST not in words
            assert sorted(path.stem for path in written(destinations[0])) == [Path(FIRST).stem, Path(SECOND).stem]

        screen.scenario(convert, the_end_names_it).run()


class TestABatchOfBrokenRecordingsWritesNothing:
    """A folder whose every recording is broken writes nothing, and its notice says so and names them all.

    The notice offers nothing to load, and the button names the run again once it is dismissed.
    """

    @pytest.fixture
    def world(self) -> World:
        folder = home_path(BROKEN_TAKES)
        return converting_world(
            (
                UnreadableRecording(destination=folder / BROKEN),
                UnreadableRecording(destination=folder / DAMAGED),
            )
        )

    def test_the_notice_names_every_broken_recording(self, screen: Screen) -> None:
        converter = screen.main.converter
        notice = converter.notice
        destinations: List[Path] = []
        named: List[str] = []

        def convert(screen: Screen) -> None:
            gather(screen, home_path(BROKEN_TAKES))
            destinations.append(Path(converter.destination()))
            named.append(converter.action())

            converter.press_action()

            screen.claim_error(BROKEN)
            screen.claim_error(DAMAGED)
            screen.bridge.expect(notice.is_shown, bool, description="the notice", timeout=RUN_TIMEOUT_SECONDS)

        def the_notice_names_them(screen: Screen) -> None:
            words = notice.words()
            notice.dismiss()
            screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")

            assert words.startswith(screen.words(NOTHING_WRITTEN))
            assert screen.words(SKIPPED_SEVERAL).format(count=2) in words
            assert BROKEN in words
            assert DAMAGED in words
            assert not converter.end_prompt.is_shown()
            assert converter.action() == named[0]
            assert written(destinations[0]) == []

        screen.scenario(convert, the_notice_names_them).run()
