from functools import lru_cache

from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource


@lru_cache(maxsize=1)
def shipped_scheme() -> ShortcutScheme:
    """The keybinding scheme the build ships, read once for the whole run."""
    return ShortcutCatalog.load(KEYBINDINGS_DIRECTORY).default


def shipped_source() -> ShortcutSource:
    """A source over the shipped scheme, which is where a panel or a dialog reads its keys.

    Reading the shipped keys keeps a case stating the gesture a user performs, so a rebind that
    changes what a press means shows up as a failure here.
    """
    return ShortcutSource(shipped_scheme())
