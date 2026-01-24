import os
import subprocess
from pathlib import Path

from sampletones.types.path import GeneralPathlike, Pathlike

from .system import System


def to_path(path: GeneralPathlike) -> Path:
    """
    Converts a path-like object to a Path instance.

    Args:
        path (GeneralPathlike): A path-like object representing a file system path.

    Returns:
        Path: A Path object.

    Raises:
        TypeError: If path is neither a string nor a Path object.
    """
    if isinstance(path, Path):
        return path

    if not isinstance(path, (str, os.PathLike)):
        raise TypeError(f"Expected path to be str or Path, got {type(path)}")

    return Path(path)


def shorten_path(path: GeneralPathlike, levels: int = 5) -> str:
    """
    Shortens a file path for display by keeping the root, first directory, and last few parts.

    If the path has fewer parts than the specified levels, returns the full path.
    Otherwise, shows root, first directory, "...", and the last (levels-2) parts.

    Args:
        path (GeneralPathlike): The path to shorten.
        levels (int): The number of path parts to keep visible. Defaults to 5.

    Returns:
        str: The shortened path string with "..." indicating omitted parts.

    Examples:
        For Windows:
        >>> sys.platform.startswith("win") and shorten_path(Path("C:/Users/user/Documents"), levels=2)  # doctest: +SKIP
        'C:\\...\\Documents'

        For Linux/macOS:
        >>> shorten_path(Path("/home/user/file.txt"), levels=3)  # doctest: +SKIP
        '/home/user/file.txt'
        >>> shorten_path(Path("/a/b/c/d/e/f/g/h"), levels=4)  # doctest: +SKIP
        '/a/.../g/h'
    """
    if not isinstance(path, (str, Path, os.PathLike)):
        raise TypeError(f"Expected path to be path-like, got {type(path)}")

    if not isinstance(levels, int) or levels <= 1:
        raise ValueError("Levels must be a positive integer greater than 1")

    path = to_path(path)
    path = path.expanduser().resolve()
    parts = path.parts
    root = parts[0]
    begin = root.rstrip(os.sep)

    if len(parts) <= levels + 1:
        return str(path)

    if levels == 2:
        return os.sep.join([begin, "...", parts[-1]])

    index = 2 - levels
    first_directory = parts[1]
    last_parts = parts[index:]
    return os.sep.join([begin, first_directory, "..."] + list(last_parts))


def get_directory(path: Pathlike) -> Path:
    """
    Returns the directory path for a given path.

    If the path is already a directory, returns it as-is.
    If the path is a file, returns its parent directory.

    Args:
        path (Pathlike): A file or directory path.

    Returns:
        Path: The directory path.
    """
    path = to_path(path)
    return path if path.is_dir() else path.parent


def open_directory_in_explorer_linux(path: Path) -> None:
    """
    Opens a directory in the default Linux file manager using xdg-open.

    If the path is a file, opens its parent directory instead.

    Args:
        path (Path): The directory or file path to open.
    """
    path = path if path.is_dir() else path.parent
    subprocess.run(["xdg-open", str(path)], check=False)


def open_file_in_explorer_linux(path: Path) -> None:
    """
    Opens a file in the Linux file manager with the file selected/highlighted.

    Detects the default file manager and uses the appropriate command to select
    the file. Supports Dolphin, Nautilus, Nemo, and Thunar. Falls back to opening
    the parent directory if the file manager doesn't support file selection.

    Args:
        path (Path): The file path to open and select in the file manager.
    """
    path_string = str(path)
    xdg_mime_result = subprocess.run(
        ["xdg-mime", "query", "default", "inode/directory"],
        capture_output=True,
        text=True,
        check=False,
    )

    if xdg_mime_result.returncode != 0:
        open_directory_in_explorer_linux(path)
        return

    desktop_file = xdg_mime_result.stdout.strip()
    file_manager_commands = {
        "org.kde.dolphin.desktop": ["dolphin", "--select", path_string],
        "dolphin.desktop": ["dolphin", "--select", path_string],
        "org.gnome.Nautilus.desktop": ["nautilus", "--select", path_string],
        "nautilus.desktop": ["nautilus", "--select", path_string],
        "nemo.desktop": ["nemo", path_string],
        "thunar.desktop": ["thunar", path_string],
    }

    command = file_manager_commands.get(desktop_file)
    if command:
        result = subprocess.run(command, check=False, capture_output=True)
        if result.returncode != 0:
            open_directory_in_explorer_linux(path)
    else:
        open_directory_in_explorer_linux(path)


def open_path_in_explorer(path: Pathlike) -> None:
    """
    Opens a path in the system's default file explorer.

    Cross-platform function that opens the file explorer with the specified path.
    For files, attempts to open the file manager with the file selected/highlighted.
    For directories, opens the directory directly.

    Behavior by platform:
    - Windows: Uses 'explorer' with /select flag for files
    - Linux: Uses xdg-open and attempts file manager-specific selection
    - macOS: Uses 'open' with -R flag for files

    Args:
        path (Pathlike): The file or directory path to open in the explorer.

    Raises:
        OSError: If the operating system is unsupported.
    """
    path = to_path(path)
    path_string = str(path)
    system = System.current()

    match system:
        case System.WINDOWS:
            select = "/select," if path.is_file() else ""
            subprocess.run(["explorer", select, path_string], check=False)
        case System.LINUX:
            if path.is_file():
                open_file_in_explorer_linux(path)
            else:
                subprocess.run(["xdg-open", path_string], check=False)
        case System.MACOS:
            select = "-R" if path.is_file() else ""
            subprocess.run(["open", select, path_string], check=False)
        case _:
            raise OSError(f"Unsupported operating system: {system}")
