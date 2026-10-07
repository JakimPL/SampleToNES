import operator
from functools import partial
from typing import Final, List, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.reconstructions.instruments.constants import FADING, NOTHING, STILL_FRAMES
from tests.screens.reconstructions.instruments.steps import give_it_a_volume, open_the_instrument, song_title
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import leave_letting_the_project_go
from tests.suite.screens.steps.reconstructions import edit_envelope, expect_open
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION, SONG

BENT_ITEM: Final[int] = 2
FLAT_PITCH: Final[str] = "0 0 0 0 0"
BEND: Final[float] = 40.0
PITCH_FLOOR: Final[int] = -128
PITCH_CEILING: Final[int] = 127

PULSE_ROWS: Final[Tuple[FeatureKey, ...]] = (
    FeatureKey.VOLUME,
    FeatureKey.ARPEGGIO,
    FeatureKey.PITCH,
    FeatureKey.HI_PITCH,
    FeatureKey.DUTY_CYCLE,
)

TRIANGLE_ROWS: Final[Tuple[FeatureKey, ...]] = (
    FeatureKey.VOLUME,
    FeatureKey.ARPEGGIO,
    FeatureKey.PITCH,
    FeatureKey.HI_PITCH,
)

NOISE_ROWS: Final[Tuple[FeatureKey, ...]] = (FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE)
PITCH_BEND: Final[str] = "reconstructions.instruments.tooltip.pitch_bend"
HI_PITCH_BEND: Final[str] = "reconstructions.instruments.tooltip.hi_pitch_bend"


class TestTheRowsEachChannelDraws:
    """Pulse and triangle tabs draw Pitch and Hi-pitch rows and the noise tab omits them; a bend field
    explains a step.

    Each channel tab shows its rows in order and a pitch stepper, and the Audition switch stays hidden.
    Hovering the Pitch and Hi-pitch fields shows their bend explanations; hovering Volume shows none.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens a reconstruction and no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_rows_per_channel_and_the_bend_explanation(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        expected = {
            ChannelName.PULSE1: PULSE_ROWS,
            ChannelName.PULSE2: PULSE_ROWS,
            ChannelName.TRIANGLE: TRIANGLE_ROWS,
            ChannelName.NOISE: NOISE_ROWS,
        }

        def each_tab_draws_its_rows(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            for channel, rows in expected.items():
                instruments.bring_forward(channel)
                screen.expect(partial(instruments.rows, channel), rows.__eq__, description=f"the rows of {channel}")
                assert instruments.offers_pitch_stepper(channel)

            assert not instruments.offers_audition()

        def a_bend_field_explains_a_step(screen: Screen) -> None:
            instruments.bring_forward(ChannelName.PULSE1)
            for feature, key in ((FeatureKey.PITCH, PITCH_BEND), (FeatureKey.HI_PITCH, HI_PITCH_BEND)):
                field = instruments.field(ChannelName.PULSE1, feature)
                screen.hand.scroll_into_view(field)
                screen.hand.hover(field)

                screen.expect(partial(screen.shows_text, screen.words(key)), bool, description=f"{key} shown")

        def the_volume_field_explains_no_bend(screen: Screen) -> None:
            field = instruments.field(ChannelName.PULSE1, FeatureKey.VOLUME)
            screen.hand.scroll_into_view(field)
            screen.hand.hover(field)
            screen.frames(STILL_FRAMES)

            assert not screen.shows_text(screen.words(PITCH_BEND))
            assert not screen.shows_text(screen.words(HI_PITCH_BEND))

        screen.scenario(each_tab_draws_its_rows, a_bend_field_explains_a_step, the_volume_field_explains_no_bend).run()


class TestAnInstrument:
    """An instrument offers the Audition switch and only its own tab, and Export follows its
    envelopes.

    The opened instrument shows the Pulse 1 tab alone, with Export unavailable. A typed volume makes
    Export available, and clearing the volume makes it unavailable again.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_no_stepper_and_export_answers_while_it_sounds(self, screen: Screen) -> None:
        """The pitch stepper stays hidden, and Export turns on or off as the volume is typed or cleared."""
        instruments = screen.reconstructions.instruments

        def its_tab_alone(screen: Screen) -> None:
            open_the_instrument(screen)

            assert not instruments.offers_pitch_stepper(ChannelName.PULSE1)
            assert [channel for channel in ChannelName if instruments.tab_shown(channel)] == [ChannelName.PULSE1]
            assert not instruments.can_export(ChannelName.PULSE1)

        def a_volume_brings_export(screen: Screen) -> None:
            edit_envelope(
                screen,
                channel=ChannelName.PULSE1,
                feature=FeatureKey.VOLUME,
                sequence=FADING,
                title=song_title(screen, unsaved=True),
            )

            screen.expect(lambda: instruments.can_export(ChannelName.PULSE1), bool, description="Export answering")

        def clearing_it_greys_export_out(screen: Screen) -> None:
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.VOLUME, NOTHING)

            screen.expect(
                lambda: instruments.can_export(ChannelName.PULSE1), operator.not_, description="Export greyed out"
            )
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == NOTHING

        screen.scenario(
            its_tab_alone,
            a_volume_brings_export,
            clearing_it_greys_export_out,
            leave_letting_the_project_go,
        ).run()


class TestDraggingAPitchBar:
    """Dragging a bar of the Pitch row sets that item to the value of the release and keeps the other items
    as they were.

    A flat pitch is typed, then one bar is dragged. The field shows the released value, clamped to the
    pitch range, for that item alone.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_the_item_takes_the_value_under_the_release(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.PITCH)
        standing: List[int] = []

        def give_it_a_flat_pitch(screen: Screen) -> None:
            give_it_a_volume(screen)
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.PITCH, FLAT_PITCH)
            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.PITCH),
                FLAT_PITCH.__eq__,
                description="the flat pitch typed",
            )

            screen.hand.scroll_into_view(graph.plot)

            standing.extend(int(item) for item in FLAT_PITCH.split())

        def drag_one_bar(screen: Screen) -> None:
            release = graph.drag_item(BENT_ITEM, start=standing[BENT_ITEM], end=BEND)

            _, under = graph.value_under(release)
            expected = [*standing]
            expected[BENT_ITEM] = min(max(round(under), PITCH_FLOOR), PITCH_CEILING)
            screen.expect(
                lambda: [int(item) for item in instruments.envelope(ChannelName.PULSE1, FeatureKey.PITCH).split()],
                expected.__eq__,
                description="one item bent",
            )
            assert expected[BENT_ITEM] != standing[BENT_ITEM]

        screen.scenario(give_it_a_flat_pitch, drag_one_bar, leave_letting_the_project_go).run()
