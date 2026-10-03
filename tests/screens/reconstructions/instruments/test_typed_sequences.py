from functools import partial
from pathlib import Path
from typing import Final, List, Optional

import pytest

from sampletones_application.tags.general import TAG_GLOBAL_THEME_INPUT_INVALID, TAG_GLOBAL_THEME_INPUT_WARNING
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS
from sampletones_core.project import ProjectContainer
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.screens.reconstructions.instruments.constants import FADING, NOTHING, STILL_FRAMES
from tests.screens.reconstructions.instruments.steps import open_the_instrument, song_title
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import save_project_as
from tests.suite.screens.steps.reconstructions import edit_envelope
from tests.suite.screens.vocabulary.instruments import TOO_LONG
from tests.suite.screens.worlds.recordings import SONG, SONG_INSTRUMENT

SAVED_SONG: Final[Path] = PROJECTS_DIRECTORY / "Saved.stp"
ASIDE: Final[Point] = Point(x=0, y=0)
LOOPING_VOLUME: Final[str] = "15 14 | 12 10"
LOOPING_DUTY: Final[str] = "0 1 | 2"
LOOP_FROM_THE_START: Final[str] = "| 15"
TWO_LOOPS: Final[str] = "15 | | 14"
NOT_A_NUMBER: Final[str] = "x"
TOO_LOUD: Final[str] = "99"
LOUDEST: Final[str] = "15"
TYPING_HINT: Final[str] = "reconstructions.instruments.message.status_sequence"
KEPT_FAMITRACKER: Final[str] = "reconstructions.instruments.template.kept_famitracker"
INVALID_INPUT: Final[str] = "Invalid PULSE1 data input for VOLUME"


def status_over(screen: Screen, item: str) -> str:
    """Moves the pointer onto ``item`` from the window's corner, which sets the status line, and reads it."""
    screen.hand.move_to(ASIDE)
    screen.hand.scroll_into_view(item)
    screen.hand.hover(item)
    return screen.status()


def saved_instrument(path: Path, name: str) -> Instrument:
    """The instrument named ``name`` in the project stored at ``path``."""
    return next(
        voice for voice in ProjectContainer.load(path).voices if isinstance(voice, Instrument) and voice.name == name
    )


class TestALoopTyped:
    """A sequence typed with "|" repeats from the item after it, and a sibling of another length from its
    own point.

    The status line explains the "|" before anything is typed. Volume and Duty cycle get one loop each;
    after Save as, the stored instrument holds each loop point.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_each_envelope_keeps_its_own_loop(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments

        def the_status_line_explains_the_bar(screen: Screen) -> None:
            open_the_instrument(screen)
            field = instruments.field(ChannelName.PULSE1, FeatureKey.VOLUME)

            hint = screen.words(TYPING_HINT).format(instrument_feature=FeatureKey.VOLUME.capitalized)
            screen.expect(partial(status_over, screen, field), hint.__eq__, description="the hint about the bar")

        def type_two_loops(screen: Screen) -> None:
            edit_envelope(
                screen,
                channel=ChannelName.PULSE1,
                feature=FeatureKey.VOLUME,
                sequence=LOOPING_VOLUME,
                title=song_title(screen, unsaved=True),
            )
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.DUTY_CYCLE, LOOPING_DUTY)

            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.DUTY_CYCLE),
                LOOPING_DUTY.__eq__,
                description="the duty cycle typed",
            )
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == LOOPING_VOLUME

        def the_project_keeps_each_loop(screen: Screen) -> None:
            save_project_as(screen, SAVED_SONG)

            envelopes = saved_instrument(SAVED_SONG, SONG_INSTRUMENT).envelopes
            assert (envelopes.volume.items, envelopes.volume.loop_point) == ((15, 14, 12, 10), 2)
            assert (envelopes.duty_cycle.items, envelopes.duty_cycle.loop_point) == ((0, 1, 2), 2)

        screen.scenario(the_status_line_explains_the_bar, type_two_loops, the_project_keeps_each_loop).run()


class TestSequencesTheFieldAnswers:
    """An unreadable sequence is refused and flagged, and a readable one is applied as written.

    A value past the range is brought into it, an empty field clears the dimension, and a sequence
    longer than an export keeps is applied with a warning naming what the export keeps. After Save as,
    the project holds the last sequence applied.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_refused_clamped_cleared_and_warned(self, screen: Screen) -> None:
        """Each kind of typed sequence gets its own answer: an error, a clamp, a clear or a warning."""
        instruments = screen.reconstructions.instruments
        long_sequence = " ".join(["8"] * (MAX_SEQUENCE_ITEMS + 1))
        plain: List[Optional[str]] = []

        def typed(sequence: str) -> None:
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.VOLUME, sequence)
            screen.frames(STILL_FRAMES)

        def theme() -> Optional[str]:
            return instruments.field_theme(ChannelName.PULSE1, FeatureKey.VOLUME)

        def unreadable_sequences_are_refused(screen: Screen) -> None:
            open_the_instrument(screen)
            plain.append(theme())

            for sequence in (TWO_LOOPS, NOT_A_NUMBER):
                typed(sequence)

                screen.claim_error(INVALID_INPUT)
                assert theme() == TAG_GLOBAL_THEME_INPUT_INVALID
                assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == sequence
                assert screen.title() == song_title(screen, unsaved=False)

        def a_loop_from_the_start_is_applied(screen: Screen) -> None:
            typed(LOOP_FROM_THE_START)

            screen.expect(screen.title, song_title(screen, unsaved=True).__eq__, description="the edit applied")
            assert theme() != TAG_GLOBAL_THEME_INPUT_INVALID
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == LOOP_FROM_THE_START

        def a_value_past_the_range_is_brought_into_it(screen: Screen) -> None:
            typed(TOO_LOUD)

            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                LOUDEST.__eq__,
                description="the loudest level written",
            )

        def a_sequence_past_every_export_is_applied_with_a_warning(screen: Screen) -> None:
            typed(long_sequence)

            screen.expect(theme, TAG_GLOBAL_THEME_INPUT_WARNING.__eq__, description="the warning")
            instruments.bring_forward(ChannelName.PULSE1)
            field = instruments.field(ChannelName.PULSE1, FeatureKey.VOLUME)
            warning = screen.words(TOO_LONG).format(
                instrument_feature=FeatureKey.VOLUME.capitalized,
                items=MAX_SEQUENCE_ITEMS + 1,
                kept=screen.words(KEPT_FAMITRACKER).format(limit=MAX_SEQUENCE_ITEMS),
            )
            screen.expect(
                partial(status_over, screen, field), warning.__eq__, description="the status naming what each keeps"
            )

        def an_empty_field_clears_it(screen: Screen) -> None:
            typed(NOTHING)

            screen.expect(theme, plain[0].__eq__, description="the warning gone")
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == NOTHING

        def the_project_keeps_what_was_applied_last(screen: Screen) -> None:
            typed(FADING)
            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                FADING.__eq__,
                description="the last sequence applied",
            )

            save_project_as(screen, SAVED_SONG)

            assert saved_instrument(SAVED_SONG, SONG_INSTRUMENT).envelopes.volume.items == (12, 8, 4)

        screen.scenario(
            unreadable_sequences_are_refused,
            a_loop_from_the_start_is_applied,
            a_value_past_the_range_is_brought_into_it,
            a_sequence_past_every_export_is_applied_with_a_warning,
            an_empty_field_clears_it,
            the_project_keeps_what_was_applied_last,
        ).run()
