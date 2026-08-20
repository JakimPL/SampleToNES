from pathlib import Path
from typing import Tuple

from sampletones_shared.utils.system.paths import open_path_in_explorer


def distinct_parents(paths: Tuple[Path, ...]) -> Tuple[Path, ...]:
    """
    Returns the directories holding the paths, each once and in first-seen order.
    """
    return tuple(dict.fromkeys(path.parent for path in paths))


class GroupedDirectoryBackend:
    """
    Reveals files by opening the directories that hold them.

    Files sharing a directory are revealed together in that directory's window, one window
    per directory, which suits file managers that open directories.
    """

    def open(self, paths: Tuple[Path, ...]) -> None:
        for directory in distinct_parents(paths):
            open_path_in_explorer(directory)
