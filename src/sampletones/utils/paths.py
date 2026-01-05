import os
import platform
import subprocess
from pathlib import Path

from sampletones.typehints import Pathlike


def shorten_path(path: Path, levels: int = 5) -> str:
    path = path.expanduser().resolve()
    parts = path.parts

    if len(parts) <= levels:
        return str(path)

    root = parts[0]
    first_dir = parts[1]
    last_parts = parts[-(levels - 2) :]

    return os.sep.join([root.rstrip(os.sep), first_dir, "..."] + list(last_parts))


def to_path(path: Pathlike) -> Path:
    if not isinstance(path, (str, Path)):
        raise TypeError(f"Expected path to be str or Path, got {type(path)}")

    if isinstance(path, str):
        path = Path(path)

    return path


def get_directory(path: Pathlike) -> Path:
    path = to_path(path)
    return path if path.is_dir() else path.parent


def open_directory_in_explorer_linux(path: Path) -> None:
    path = path if path.is_dir() else path.parent
    subprocess.run(["xdg-open", str(path)], check=False)


def open_file_in_explorer_linux(path: Path) -> None:
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
    path = to_path(path)
    path_string = str(path)
    system = platform.system()

    if system == "Windows":
        select = "/select," if path.is_file() else ""
        subprocess.run(["explorer", select, path_string], check=False)
    elif system == "Darwin":
        select = "-R" if path.is_file() else ""
        subprocess.run(["open", select, path_string], check=False)
    else:
        if path.is_file():
            open_file_in_explorer_linux(path)
        else:
            subprocess.run(["xdg-open", path_string], check=False)
