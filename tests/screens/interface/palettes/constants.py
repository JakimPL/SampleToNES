from typing import Final, Tuple

from sampletones_application.categories.hierarchy import Tab

SETTLING_FRAMES: Final[int] = 10
TAB_FRAMES: Final[int] = 10
EVERY_TAB: Final[Tuple[Tab, ...]] = (Tab.MAIN, Tab.INSTRUCTIONS, Tab.RECONSTRUCTIONS, Tab.SEQUENCER)
