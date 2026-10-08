import operator
from typing import List

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.main import convert_alone, home_path
from automation.steps.reconstructions import (
    converted,
    edited_title,
    expect_open,
    first_level_raised,
    leading,
    raise_the_first_level,
    stored_levels,
)
from sampletones_core.constants.enums import ChannelName
from tests.screens.prompts.keyboard.steps import enter, escape, tab
from tests.suite.screens.worlds.recordings import BASS, LEAD, OPEN_RECONSTRUCTION


class TestTheLoadChainFromTheKeyboard:
    """The keys answer Load at a run's end, and the question about unsaved changes that Load opens.

    The scenario edits the open reconstruction and converts a recording. Tab and Enter choose Load, which
    asks about the changes. Escape keeps the edited reconstruction open. After a second conversion, Tab and
    Enter choose Save, which writes the edit and opens the conversion.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Starts with the reconstruction open and no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_escape_keeps_the_edits_and_the_keys_then_save_and_load(self, screen: Screen) -> None:
        converter = screen.main.converter
        prompt = screen.reconstructions.unsaved_prompt
        standing: List[int] = []

        def edit_the_open_reconstruction(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            standing.extend(stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE1))

            raise_the_first_level(screen, ChannelName.PULSE1, title=edited_title(screen, OPEN_RECONSTRUCTION))

        def load_from_the_keyboard(screen: Screen, recording: str) -> None:
            convert_alone(
                screen,
                home_path(recording),
                channel=ChannelName.PULSE1,
                replacing=[home_path(BASS), home_path(LEAD)],
            )
            tab(screen, 1)
            enter(screen)

            screen.expect(prompt.is_shown, bool, description="the question about unsaved changes")
            assert not converter.end_prompt.is_shown()

        def escape_keeps_the_edited_one(screen: Screen) -> None:
            load_from_the_keyboard(screen, BASS)

            escape(screen)

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert screen.title() == edited_title(screen, OPEN_RECONSTRUCTION)
            assert screen.reconstructions.shows_open(OPEN_RECONSTRUCTION)

        def save_and_load_from_the_keyboard(screen: Screen) -> None:
            load_from_the_keyboard(screen, LEAD)

            tab(screen, 1)
            enter(screen)

            expect_open(screen, converted(home_path(LEAD)))
            saved = stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE1)
            assert leading(saved, standing) == first_level_raised(standing)

        screen.scenario(
            edit_the_open_reconstruction,
            escape_keeps_the_edited_one,
            save_and_load_from_the_keyboard,
        ).run()
