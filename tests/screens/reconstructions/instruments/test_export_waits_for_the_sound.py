from typing import Final, Tuple

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.exports import leaving_asks_nothing
from automation.steps.reconstructions import load_from_the_browser
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.worlds.recordings import LONG_RECONSTRUCTION, alternating_document_world

CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())


@pytest.fixture(name="world")
def world_fixture() -> World:
    """The home holds the two-minute reconstruction over three recordings taking turns."""
    return alternating_document_world()


@pytest.fixture(name="startup")
def startup_fixture() -> Startup:
    """The application opens with no reconstruction and no project."""
    return Startup(reconstruction=None, project=None)


class TestAnExportAskedRightAfterAnOpening:
    """The instruments panel offers an export once the opening's sound has landed, and nothing before.

    An opening sends the document's sound and its envelopes to the worker together, so the panel
    draws no bars and offers no export until they land. The scenario opens the two-minute document
    from the browser, reads the export buttons while the sound is on its way, waits for it to land,
    and reads them again.
    """

    def test_the_export_answers_once_the_sound_has_landed(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments

        def exportable() -> Tuple[ChannelName, ...]:
            return tuple(channel for channel in CHANNELS if instruments.can_export(channel))

        def open_it_and_find_no_export_yet(screen: Screen) -> None:
            load_from_the_browser(screen, LONG_RECONSTRUCTION)

            screen.expect(
                lambda: screen.reconstructions.shows_open(LONG_RECONSTRUCTION),
                bool,
                description=f"{LONG_RECONSTRUCTION.name} open",
            )
            assert not screen.sound_settled()
            assert exportable() == ()

        def the_export_answers_with_the_sound(screen: Screen) -> None:
            screen.expect(screen.sound_settled, bool, description="the sound landed")

            offered = screen.expect(exportable, bool, description="an export offered")
            assert offered is not None
            assert all(instruments.envelope(channel, FeatureKey.VOLUME) for channel in offered)

        screen.scenario(open_it_and_find_no_export_yet, the_export_answers_with_the_sound, leaving_asks_nothing).run()
