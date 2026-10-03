import operator
from typing import Tuple

from sampletones_shared.display import Resolution
from tests.screens.interface.display.constants import SIZE_SEPARATOR
from tests.suite.screens.dearpygui.items.viewport import read_viewport, read_viewport_decorated
from tests.suite.screens.screen import Screen


def size_named(label: str) -> Resolution:
    """The window size a Resolution entry names, written width first."""
    width, height = label.split(SIZE_SEPARATOR)
    return Resolution(width=int(width), height=int(height))


def window_size(screen: Screen) -> Tuple[int, int]:
    """The width and height of the window in pixels."""
    viewport = screen.bridge.ask(read_viewport)
    return round(viewport.width), round(viewport.height)


def window_position(screen: Screen) -> Tuple[int, int]:
    """Where the window's client area stands on the screen, left then top."""
    viewport = screen.bridge.ask(read_viewport)
    return round(viewport.x), round(viewport.y)


def framed(screen: Screen) -> bool:
    """Whether the window has its frame."""
    return screen.bridge.ask(read_viewport_decorated)


def open_display_settings(screen: Screen) -> None:
    """Opens Display settings and waits for it to show."""
    settings = screen.display_settings
    settings.open()
    screen.expect(settings.is_shown, bool, description="Display settings")


def another_size(screen: Screen) -> str:
    """A size the Resolution list offers other than the one it names."""
    settings = screen.display_settings
    current = settings.resolution()
    return next(label for label in settings.resolutions() if label != current)


def kept(screen: Screen) -> None:
    """Waits for the countdown a window change starts, and presses Keep."""
    settings = screen.display_settings
    screen.expect(settings.countdown_shown, bool, description="the countdown")
    settings.keep()
    screen.expect(settings.countdown_shown, operator.not_, description="the countdown gone")
