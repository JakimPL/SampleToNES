from typing import Final, List, Tuple

import pytest

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.general import TAG_GLOBAL_THEME_INPUT_WARNING
from sampletones_core.constants.enums import FeatureKey
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS
from sampletones_shared.paths.extensions import EXT_FILE_BITPHASE, EXT_FILE_MODULE
from tests.screens.exports.progress.constants import INSTRUMENT_CHANNEL, MODULE_EXPORTED
from tests.screens.exports.progress.steps import folder, written_project
from tests.suite.bitphase import parse_btp
from tests.suite.famitracker import parse_ftm
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import open_voice
from tests.suite.screens.vocabulary.instruments import TOO_LONG
from tests.suite.screens.worlds.songs import (
    LONG_ENVELOPES_PROJECT,
    LONG_ITEMS,
    LONG_VOICE,
    MIDDLING_ITEMS,
    MIDDLING_VOICE,
)

BITPHASE_EXPORTED: Final[str] = "global.dialog.message.bitphase_project_exported_successfully"
SHORTENED_PROJECT: Final[str] = "global.dialog.template.export_truncated"
KEPT_BY_FAMITRACKER: Final[str] = "reconstructions.instruments.template.kept_famitracker"
KEPT_BY_BITPHASE: Final[str] = "reconstructions.instruments.template.kept_bitphase"
KEPT_BY_PRESET: Final[str] = "reconstructions.instruments.template.kept_bitphase_preset"
KEPT_SEPARATOR: Final[str] = "reconstructions.instruments.template.kept_separator"
ASIDE: Final[Point] = Point(x=0, y=0)


def written_for(names: List[str], voices: Tuple[str, ...]) -> int:
    """Counts the instruments listed under ``names`` that were written for one of ``voices``."""
    return sum(1 for name in names if any(name == voice or name.startswith(f"{voice} (") for voice in voices))


class TestShortenedEnvelopes:
    """An envelope longer than a format stores shows, in its field's status, each export that cuts it and what each
    keeps; a project export says how many of its instruments it shortened.

    The long voice runs past every format's limit, and the middling one past FamiTracker's alone. A format writes a
    voice as one instrument or several, so the count in the notice is read against the instruments the file lists.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=LONG_ENVELOPES_PROJECT)

    def test_the_status_and_the_notices_name_the_cuts(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        into = folder("shortened")

        def status_of(voice: str) -> str:
            open_voice(screen, voice)
            screen.expect(
                lambda: instruments.tab_label(INSTRUMENT_CHANNEL),
                voice.__eq__,
                description=f"{voice} open",
            )
            screen.hand.move_to(ASIDE)
            instruments.hover_field(INSTRUMENT_CHANNEL, FeatureKey.VOLUME)
            return screen.expect(screen.status, bool, description=f"the status of {voice}'s volume")

        def too_long(items: int, *kept: str) -> str:
            return screen.words(TOO_LONG).format(
                instrument_feature=FeatureKey.VOLUME.capitalized,
                items=items,
                kept=screen.words(KEPT_SEPARATOR).join(kept),
            )

        def the_long_voice_names_every_format(screen: Screen) -> None:
            status = status_of(LONG_VOICE)

            assert status == too_long(
                LONG_ITEMS,
                screen.words(KEPT_BY_FAMITRACKER).format(limit=MAX_SEQUENCE_ITEMS),
                screen.words(KEPT_BY_BITPHASE).format(limit=MAX_MACRO_LENGTH),
                screen.words(KEPT_BY_PRESET).format(limit=MAX_MACRO_LENGTH),
            )
            assert instruments.field_theme(INSTRUMENT_CHANNEL, FeatureKey.VOLUME) == TAG_GLOBAL_THEME_INPUT_WARNING

        def the_middling_voice_names_famitracker_alone(screen: Screen) -> None:
            status = status_of(MIDDLING_VOICE)

            assert status == too_long(
                MIDDLING_ITEMS,
                screen.words(KEPT_BY_FAMITRACKER).format(limit=MAX_SEQUENCE_ITEMS),
            )

        def a_bitphase_project_shortens_one(screen: Screen) -> None:
            destination = into / f"{LONG_ENVELOPES_PROJECT.stem}{EXT_FILE_BITPHASE}"
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_BITPHASE)

            words = written_project(screen, BITPHASE_EXPORTED, destination)
            names = [instrument.name for instrument in parse_btp(destination.read_bytes(), []).instruments]
            assert (
                screen.words(SHORTENED_PROJECT).format(
                    instruments=written_for(names, (LONG_VOICE,)),
                    frames=MAX_MACRO_LENGTH,
                    source_frames=LONG_ITEMS,
                )
                in words
            )

        def a_module_shortens_both(screen: Screen) -> None:
            destination = into / f"{LONG_ENVELOPES_PROJECT.stem}{EXT_FILE_MODULE}"
            screen.answer_next_dialog(DialogKind.SAVE, destination)

            screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_FAMITRACKER)

            words = written_project(screen, MODULE_EXPORTED, destination)
            names = [instrument.name for instrument in parse_ftm(destination.read_bytes()).instruments]
            assert (
                screen.words(SHORTENED_PROJECT).format(
                    instruments=written_for(names, (LONG_VOICE, MIDDLING_VOICE)),
                    frames=MAX_SEQUENCE_ITEMS,
                    source_frames=LONG_ITEMS,
                )
                in words
            )

        screen.scenario(
            the_long_voice_names_every_format,
            the_middling_voice_names_famitracker_alone,
            a_bitphase_project_shortens_one,
            a_module_shortens_both,
        ).run()
