from itertools import takewhile
from typing import Final, Sequence, Tuple

from sampletones_tools.calibration.variants import LABEL_SEPARATOR

from .model import BoardColumn

SHARING_NAMES: Final[int] = 2


def shared_words(names: Sequence[str]) -> Tuple[str, ...]:
    """
    The words every column's name starts with, where two columns or more stand side by side.

    A variant's label joins the settings it departs from the base by onto the base's own words, so
    the words a group's names share say what its columns hold in common, and the words past them tell
    each column apart. A lone column shares nothing and keeps every word of its name.

    Args:
        names: The columns' names, each a run of words the label separator joins.

    Returns:
        The words every name starts with, in the order the names spell them.
    """
    if len(names) < SHARING_NAMES:
        return ()

    spelled = zip(*(name.split(LABEL_SEPARATOR) for name in names))
    return tuple(words[0] for words in takewhile(_alike, spelled))


def heading_column(name: str, prefix: Sequence[str]) -> BoardColumn:
    """The column called ``name``, its heading holding the words of the name past ``prefix``."""
    return BoardColumn(name=name, words=tuple(name.split(LABEL_SEPARATOR)[len(prefix) :]))


def _alike(words: Tuple[str, ...]) -> bool:
    return len(set(words)) == 1
