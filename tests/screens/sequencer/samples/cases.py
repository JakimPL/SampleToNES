from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Tuple

from tests.screens.sequencer.samples.steps import (
    add_by_double_click,
    add_from_the_reconstruction_menu,
    add_from_the_reconstructions_browser,
    add_from_the_sequencer_browser,
    add_from_the_voice_menu,
    add_from_the_voices_list,
)
from tests.suite.screens.screen import Screen


@dataclass(frozen=True)
class Door:
    """One way a reader adds a reconstruction file to the project's voices.

    Attributes:
        name: What the row is called among the scenarios.
        add: Adds the reconstruction stored at a path through this door.
    """

    name: str
    add: Callable[[Screen, Path], None]


DOORS: Final[Tuple[Door, ...]] = (
    Door("reconstructions_browser", add_from_the_reconstructions_browser),
    Door("sequencer_browser", add_from_the_sequencer_browser),
    Door("double_click", add_by_double_click),
    Door("voices_list", add_from_the_voices_list),
    Door("reconstruction_menu", add_from_the_reconstruction_menu),
    Door("voice_menu", add_from_the_voice_menu),
)
