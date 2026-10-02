import operator
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.application import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import StoredReconstruction
from tests.suite.screens.steps.main import RUN_TIMEOUT_SECONDS, convert_alone, home_path
from tests.suite.screens.steps.reconstructions import (
    converted,
    expect_open,
    first_level_raised,
    leading,
    load_from_the_browser,
    marked,
    raise_the_first_level,
    stored_levels,
    titled,
)
from tests.suite.screens.world import BASS, LEAD, OPEN_RECONSTRUCTION

PULSES: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.PULSE2)
LOAD_TITLE: Final[str] = "global.dialog.title.load_unsaved_reconstruction"
LOAD_MESSAGE: Final[str] = "global.dialog.message.load_unsaved_reconstruction"
REPLACED_MESSAGE: Final[str] = "global.dialog.message.load_replaced_reconstruction"
SAVE: Final[str] = "global.dialog.label.save"
DISCARD: Final[str] = "global.dialog.label.discard"
CANCEL: Final[str] = "global.dialog.label.cancel"


def convert_and_ask_to_load(screen: Screen, recording: str) -> None:
    """Converts the home's ``recording`` alone on Pulse 1, leaving a volume to edit, and answers Load at the end."""
    converter = screen.main.converter
    convert_alone(
        screen,
        home_path(recording),
        channel=ChannelName.PULSE1,
        replacing=[home_path(BASS), home_path(LEAD)],
    )

    converter.end_prompt.confirm()

    screen.expect(converter.end_prompt.is_shown, operator.not_, description="the end answered")


def load_question(screen: Screen) -> Tuple[str, str, Tuple[str, ...]]:
    """The question about unsaved changes a load asks: its title, its words and its answers."""
    return (
        screen.words(LOAD_TITLE),
        screen.words(LOAD_MESSAGE),
        (screen.words(SAVE), screen.words(DISCARD), screen.words(CANCEL)),
    )


def asked(screen: Screen) -> Tuple[str, str, Tuple[str, ...]]:
    prompt = screen.reconstructions.unsaved_prompt
    screen.expect(prompt.is_shown, bool, description="the question about unsaved changes")
    return prompt.title(), prompt.words(), prompt.answers()


def edited_title(screen: Screen) -> str:
    return titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True))


class TestLoadingAConversionOverAnEditedReconstruction:
    """Load at a run's end, with an edited reconstruction open, asks about its changes first.

    Save writes them and loads the conversion, Discard loads it and leaves the file as it was, and
    Cancel keeps the edited reconstruction open.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_cancel_keeps_the_edits_and_save_writes_them_before_loading(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        typed: List[str] = []
        stored: List[bytes] = []
        standing: List[int] = []

        def edit_the_open_reconstruction(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            stored.append(OPEN_RECONSTRUCTION.read_bytes())
            standing.extend(stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE1))

            typed.append(raise_the_first_level(screen, ChannelName.PULSE1, title=edited_title(screen)))

        def load_asks_about_the_changes(screen: Screen) -> None:
            convert_and_ask_to_load(screen, BASS)

            assert asked(screen) == load_question(screen)

        def cancel_keeps_the_edited_one_open(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert screen.title() == edited_title(screen)
            assert reconstructions.shows_open(OPEN_RECONSTRUCTION)
            assert reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == typed[0]
            assert OPEN_RECONSTRUCTION.read_bytes() == stored[0]

        def save_writes_the_changes_and_loads_the_next(screen: Screen) -> None:
            convert_and_ask_to_load(screen, LEAD)
            assert asked(screen) == load_question(screen)

            prompt.save()

            expect_open(screen, converted(home_path(LEAD)))
            assert screen.title() == titled(screen, converted(home_path(LEAD)).name)
            assert not prompt.is_shown()
            saved = stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE1)
            assert leading(saved, standing) == first_level_raised(standing)

        screen.scenario(
            edit_the_open_reconstruction,
            load_asks_about_the_changes,
            cancel_keeps_the_edited_one_open,
            save_writes_the_changes_and_loads_the_next,
        ).run()

    def test_discard_loads_the_conversion_and_leaves_the_file(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        stored: List[bytes] = []
        standing: Dict[ChannelName, List[int]] = {}

        def edit_the_open_reconstruction(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            stored.append(OPEN_RECONSTRUCTION.read_bytes())
            standing.update({channel: stored_levels(OPEN_RECONSTRUCTION, channel) for channel in PULSES})

            raise_the_first_level(screen, ChannelName.PULSE1, title=edited_title(screen))

        def discard_loads_the_conversion(screen: Screen) -> None:
            convert_and_ask_to_load(screen, BASS)
            assert asked(screen) == load_question(screen)

            prompt.confirm()

            expect_open(screen, converted(home_path(BASS)))
            assert screen.title() == titled(screen, converted(home_path(BASS)).name)
            assert OPEN_RECONSTRUCTION.read_bytes() == stored[0]

        def the_file_takes_a_save_made_later(screen: Screen) -> None:
            load_from_the_browser(screen, OPEN_RECONSTRUCTION)
            expect_open(screen, OPEN_RECONSTRUCTION)
            raise_the_first_level(screen, ChannelName.PULSE2, title=edited_title(screen))

            reconstructions.save_from_menu()

            screen.expect(screen.title, titled(screen, OPEN_RECONSTRUCTION.name).__eq__, description="the save landed")
            second = standing[ChannelName.PULSE2]
            assert leading(stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE2), second) == first_level_raised(second)
            assert stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE1) == standing[ChannelName.PULSE1]

        screen.scenario(
            edit_the_open_reconstruction,
            discard_loads_the_conversion,
            the_file_takes_a_save_made_later,
        ).run()


class TestAConversionWrittenOverTheOpenFile:
    """A run writing over the edited reconstruction open offers Discard and Cancel alone, Cancel keeping the edits."""

    def test_only_discard_and_cancel_and_each_does_what_it_says(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        converter = screen.main.converter
        prompt = reconstructions.replaced_prompt
        drawn: Dict[str, str] = {}

        def convert_and_load(screen: Screen) -> None:
            convert_and_ask_to_load(screen, BASS)

            expect_open(screen, converted(home_path(BASS)))
            drawn["converted"] = screen.expect(
                lambda: reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                bool,
                description="Pulse 1's volume drawn",
            )

        def edit_it(screen: Screen) -> None:
            drawn["edit"] = raise_the_first_level(
                screen,
                ChannelName.PULSE1,
                title=titled(screen, marked(converted(home_path(BASS)).name, unsaved=True)),
            )

        def convert_over_it(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.MAIN)
            converter.press_action()
            screen.expect(converter.overwrite_prompt.is_shown, bool, description="the question about replacing")
            converter.overwrite_prompt.confirm()
            screen.bridge.expect(
                converter.end_prompt.is_shown, bool, description="the run's end", timeout=RUN_TIMEOUT_SECONDS
            )

            converter.end_prompt.confirm()

            screen.expect(prompt.is_shown, bool, description="the question about the file written over")
            assert prompt.title() == screen.words(LOAD_TITLE)
            assert prompt.words() == screen.words(REPLACED_MESSAGE)
            assert prompt.answers() == (screen.words(DISCARD), screen.words(CANCEL))
            assert not reconstructions.unsaved_prompt.is_shown()

        def cancel_keeps_the_edits(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert screen.title() == titled(screen, marked(converted(home_path(BASS)).name, unsaved=True))
            assert reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == drawn["edit"]

        def discard_loads_what_the_run_wrote(screen: Screen) -> None:
            convert_over_it(screen)

            prompt.confirm()

            screen.expect(
                screen.title,
                titled(screen, converted(home_path(BASS)).name).__eq__,
                description="the conversion loaded",
            )
            assert reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == drawn["converted"]

        screen.scenario(
            convert_and_load,
            edit_it,
            convert_over_it,
            cancel_keeps_the_edits,
            discard_loads_what_the_run_wrote,
        ).run()


class TestReloadingACleanReconstruction:
    """A reconstruction with nothing unsaved loads its own file again without a question, as the file now stands."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_the_file_changed_on_disk_loads_as_it_stands(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        standing: List[str] = []

        def change_the_file_behind_it(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            standing.append(reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME))
            raise_the_first_level(screen, ChannelName.PULSE1, title=edited_title(screen))
            reconstructions.save_from_menu()
            screen.expect(screen.title, titled(screen, OPEN_RECONSTRUCTION.name).__eq__, description="the save landed")

            StoredReconstruction(OPEN_RECONSTRUCTION).write()

        def reloading_asks_nothing(screen: Screen) -> None:
            load_from_the_browser(screen, OPEN_RECONSTRUCTION)

            screen.expect(
                lambda: reconstructions.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                standing[0].__eq__,
                description="the file as it now stands",
            )
            assert not reconstructions.unsaved_prompt.is_shown()
            assert screen.title() == titled(screen, OPEN_RECONSTRUCTION.name)

        screen.scenario(change_the_file_behind_it, reloading_asks_nothing).run()
