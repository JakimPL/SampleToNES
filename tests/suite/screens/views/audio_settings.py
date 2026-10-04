from typing import Final, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.settings import (
    TAG_SETTINGS_AUDIO_BUTTON_APPLY,
    TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN,
    TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB,
    TAG_SETTINGS_AUDIO_WINDOW,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.reading import read_item, read_value
from tests.suite.screens.dearpygui.reach import UnreachableError

COLOR: Final[str] = "color"
MIDDLE: Final[float] = 0.5


class AudioSettings:
    """The Audio settings dialog, as far as its master gain and Apply: the slider, the line reading its level
    in decibels, and the button that applies the choices.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def is_shown(self) -> bool:
        """Whether the dialog stands on the screen."""
        return self._bridge.ask(lambda: read_item(TAG_SETTINGS_AUDIO_WINDOW)).shown

    def apply(self) -> None:
        """Clicks Apply."""
        self._hand.click(TAG_SETTINGS_AUDIO_BUTTON_APPLY)

    def gain(self) -> float:
        """The master gain the slider stands at."""
        return float(self._bridge.ask(lambda: read_value(TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN)))

    def decibels(self) -> str:
        """What the line under the slider reads."""
        return str(self._bridge.ask(lambda: read_value(TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB)))

    def decibels_color(self) -> Tuple[float, ...]:
        """The color the line under the slider is drawn in."""
        return tuple(
            float(part)
            for part in self._bridge.ask(
                lambda: dpg.get_item_configuration(TAG_SETTINGS_AUDIO_TEXT_MASTER_GAIN_DB)[COLOR]
            )
        )

    def drag_gain(self, start: float, end: float) -> None:
        """Drags the slider from ``start`` to ``end``, each a fraction of its width.

        A fraction beyond 0 or 1 drags past the end of the slider.

        Raises:
            UnreachableError: If the slider reports no box.
        """
        box = self._bridge.ask(lambda: read_item(TAG_SETTINGS_AUDIO_SLIDER_MASTER_GAIN).rect)
        if box is None:
            raise UnreachableError("The master gain slider reports no box")

        middle = round(box.y + box.height * MIDDLE)
        self._hand.drag(
            Point(x=round(box.x + box.width * start), y=middle),
            Point(x=round(box.x + box.width * end), y=middle),
        )
