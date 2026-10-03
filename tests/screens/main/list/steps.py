from functools import partial
from pathlib import Path

from tests.screens.main.list.constants import FREQUENCY
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import explorer_row
from tests.suite.screens.worlds.home import HomeFile


def take(index: int) -> str:
    """Returns the file name of the numbered take, such as ``take07.wav``."""
    return f"take{index:02d}.wav"


def recording(path: Path, seconds: float) -> HomeFile:
    """Returns a seeded tone recording of ``seconds`` to be written at ``path``."""
    return Recording(destination=path, seconds=seconds, frequency=FREQUENCY)


def gather(screen: Screen, *paths: Path) -> None:
    """Ctrl-clicks each of ``paths`` in the explorer and waits for its row and for the folder read to end."""
    converter = screen.main.converter
    for path in paths:
        screen.explorer.ctrl_click(explorer_row(screen, path))
        screen.expect(partial(converter.list.has_row, path), bool, description=f"{path.name} gathered")
        screen.expect(lambda: not converter.scan_shown(), bool, description="the read done")
