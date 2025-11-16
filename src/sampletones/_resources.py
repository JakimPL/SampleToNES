import importlib.resources as resources
import sys
import tempfile
from pathlib import Path
from typing import Optional


def meipass_icon_path(icon_name: str) -> Optional[Path]:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_base = Path(sys._MEIPASS)
        candidate_paths = (
            meipass_base / "sampletones" / "icons" / icon_name,
            meipass_base / "icons" / icon_name,
            meipass_base / icon_name,
        )
        for candidate in candidate_paths:
            if candidate.exists():
                return candidate
    return None


def get_icon_path(icon_name: str) -> str:
    path_from_meipass = meipass_icon_path(icon_name)
    if path_from_meipass is not None:
        return str(path_from_meipass)
    package_icon_path = resources.files("sampletones").joinpath("icons", icon_name)
    if package_icon_path.is_file():
        return str(package_icon_path)
    icon_bytes = package_icon_path.read_bytes()
    temp_directory_path = Path(tempfile.gettempdir()) / "sampletones_icons"
    temp_directory_path.mkdir(parents=True, exist_ok=True)
    temp_icon_path = temp_directory_path / icon_name
    temp_icon_path.write_bytes(icon_bytes)
    return str(temp_icon_path)


def get_icon_bytes(icon_name: str) -> bytes:
    path_from_meipass = meipass_icon_path(icon_name)
    if path_from_meipass is not None:
        return path_from_meipass.read_bytes()
    package_icon_path = resources.files("sampletones").joinpath("icons", icon_name)
    return package_icon_path.read_bytes()
