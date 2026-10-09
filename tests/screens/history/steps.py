from typing import Callable, Dict, List, Tuple

from automation.screen import Screen
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey

Fields = Dict[ChannelName, str]


def volume_fields(
    screen: Screen,
    channels: Tuple[ChannelName, ...],
) -> Fields:
    """What the volume field of each of ``channels`` reads on the Reconstructions tab."""
    instruments = screen.reconstructions.instruments
    return {channel: instruments.envelope(channel, FeatureKey.VOLUME) for channel in channels}


def press_on_the_sequencer(
    screen: Screen,
    shortcut_id: ShortcutId,
) -> None:
    """Brings the Sequencer forward and presses the keys of ``shortcut_id``."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.press_shortcut(shortcut_id)


def expect_reading(
    screen: Screen,
    reading: Callable[[], object],
    expected: object,
    description: str,
) -> None:
    """Waits until ``reading`` gives ``expected``."""
    screen.expect(reading, expected.__eq__, description=description)


def history_count(screen: Screen) -> int:
    """How many lines the History card draws."""
    return len(screen.sequencer.history.lines())


def expect_lines(
    screen: Screen,
    count: int,
) -> None:
    """Waits until the History card draws ``count`` lines."""
    screen.expect(lambda: history_count(screen), count.__eq__, description=f"{count} history lines")


def leading(
    fields: Fields,
    typed: Dict[ChannelName, str],
) -> Dict[ChannelName, List[str]]:
    """The leading values of each field, as many as were typed into it.

    A typed volume lands with the release its last frame writes, so the leading values are what
    a typed sequence is read back by.
    """
    return {channel: fields[channel].split()[: len(sequence.split())] for channel, sequence in typed.items()}


def typed_values(typed: Dict[ChannelName, str]) -> Dict[ChannelName, List[str]]:
    """The values of each typed sequence, as :func:`leading` reads them back."""
    return {channel: sequence.split() for channel, sequence in typed.items()}
