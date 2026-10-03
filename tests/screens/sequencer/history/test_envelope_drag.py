from typing import Final, List, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.sequencer.history.constants import PAD_POSITION, POSITION_MARK
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, open_voice
from tests.suite.screens.views.history import HistoryLine
from tests.suite.screens.worlds.songs import PAD

VOLUME_LETTER: Final[str] = "v"
ARPEGGIO_LETTER: Final[str] = "a"
QUIET: Final[float] = 4.0
ARPEGGIO_STEP: Final[float] = 5.0
DRAGGED_ITEM: Final[int] = 1


def position_color(line: HistoryLine, position: str) -> Tuple[float, ...]:
    """The color of the piece of ``line`` naming the voice by its ``position``."""
    return next(segment.color for segment in line.segments if segment.words.rstrip(POSITION_MARK) == position)


class TestAnEnvelopeDragIsOneEntry:
    """A drag across an instrument's envelope makes one history entry naming the voice and the dimension.

    The pad instrument is opened and its volume envelope is dragged: one entry appears, naming the
    instrument by its number in the color of its kind. A drag across the arpeggio envelope adds a second
    entry. One undo takes back the arpeggio drag only, and the project is left.
    """

    def test_one_entry_per_dimension(self, screen: Screen) -> None:
        """Each drag makes exactly one entry, and one undo reverts one drag."""
        instruments = screen.reconstructions.instruments
        history = screen.sequencer.history
        lines: List[int] = []
        standing: List[str] = []

        def drag(feature: FeatureKey, end: float) -> None:
            graph = instruments.graph(ChannelName.PULSE1, feature)
            screen.hand.scroll_into_view(graph.plot)
            graph.drag_item(DRAGGED_ITEM, start=0.0, end=end)

        def drag_the_volume(screen: Screen) -> None:
            open_voice(screen, PAD)
            screen.expect(instruments.offers_audition, bool, description="the instrument open")
            lines.append(len(history.lines()))

            drag(FeatureKey.VOLUME, QUIET)

            after = screen.expect(history.lines, lambda found: len(found) == lines[0] + 1, description="one entry")
            assert position_color(after[0], PAD_POSITION) == screen.sequencer.voices.kind_color(PAD)
            assert VOLUME_LETTER in after[0].words.split()

        def drag_the_arpeggio(screen: Screen) -> None:
            standing.append(instruments.envelope(ChannelName.PULSE1, FeatureKey.ARPEGGIO))

            drag(FeatureKey.ARPEGGIO, ARPEGGIO_STEP)

            after = screen.expect(history.lines, lambda found: len(found) == lines[0] + 2, description="a second entry")
            assert ARPEGGIO_LETTER in after[0].words.split()

        def one_undo_takes_one_back(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)

            history.undo()

            screen.expect(lambda: history.lines()[1].current, bool, description="one step back")
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.ARPEGGIO) == standing[0]

        screen.scenario(drag_the_volume, drag_the_arpeggio, one_undo_takes_one_back, leave_letting_the_project_go).run()
