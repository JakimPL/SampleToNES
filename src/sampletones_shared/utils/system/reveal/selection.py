import importlib.util
from typing import Final, Sequence

from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import open_path_in_explorer, to_path
from sampletones_shared.utils.system.system import System

from .grouped import GroupedDirectoryBackend
from .protocol import RevealBackend

JEEPNEY_MODULE: Final[str] = "jeepney"


def open_paths_in_explorer(paths: Sequence[Pathlike]) -> None:
    """
    Reveals the given paths in the system's default file explorer.

    A single path opens the explorer on it the way :func:`open_path_in_explorer` does. Several
    paths go through the environment's reveal backend: a Linux session whose file manager
    offers ``org.freedesktop.FileManager1`` opens one window with every file selected, and any
    other environment opens one window per directory holding the files.

    Args:
        paths: The file paths to reveal.

    Raises:
        ValueError: If at least one path is required.
    """
    normalized = tuple(to_path(path) for path in paths)
    if not normalized:
        raise ValueError("At least one path is required")

    if len(normalized) == 1:
        open_path_in_explorer(normalized[0])
        return

    select_reveal_backend().open(normalized)


def select_reveal_backend() -> RevealBackend:
    """
    Returns the reveal backend that fits the running environment.

    Linux sessions whose file manager answers the ``FileManager1`` probe reveal every path in
    one window with all of them selected; every other environment reveals one window per
    directory holding the paths. The service is probed at selection time, so the grouped
    backend serves sessions where it is absent.
    """
    if System.current() == System.LINUX and importlib.util.find_spec(JEEPNEY_MODULE) is not None:
        from .file_manager1 import FileManager1Backend

        if FileManager1Backend.answers():
            return FileManager1Backend()

    return GroupedDirectoryBackend()
