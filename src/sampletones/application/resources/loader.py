import sys
import tempfile
from importlib import resources
from pathlib import Path
from typing import Optional

from sampletones.constants.application import SAMPLETONES_PACKAGE_NAME
from sampletones.constants.paths import ASSETS_DIRECTORY


class ResourceLoader:
    def __init__(self, resource_directory: str) -> None:
        self.base_directory = Path(SAMPLETONES_PACKAGE_NAME) / ASSETS_DIRECTORY
        self.resource_directory = resource_directory

    def _get_meipass_path(self, resource_name: str) -> Optional[Path]:
        meipass = getattr(sys, "_MEIPASS", None)
        if getattr(sys, "frozen", False) and meipass is not None:
            meipass_base = Path(meipass)
            candidate_paths = (
                meipass_base / self.base_directory / self.resource_directory / resource_name,
                meipass_base / self.resource_directory / resource_name,
                meipass_base / resource_name,
            )
            for candidate in candidate_paths:
                if candidate.exists():
                    return candidate

        return None

    def _get_package_path(self, resource_name: str) -> Path:
        module_name = ".".join(self.base_directory.parts)
        return Path(str(resources.files(module_name).joinpath(self.resource_directory, resource_name)))

    def get_path(self, resource_name: str) -> str:
        path_from_meipass = self._get_meipass_path(resource_name)
        if path_from_meipass is not None:
            return str(path_from_meipass)

        package_resource_path = self._get_package_path(resource_name)
        if package_resource_path.is_file():
            return str(package_resource_path)

        resource_bytes = package_resource_path.read_bytes()
        temp_directory_path = Path(tempfile.gettempdir()) / f"{ASSETS_DIRECTORY}_{self.resource_directory}"
        temp_directory_path.mkdir(parents=True, exist_ok=True)
        temp_resource_path = temp_directory_path / resource_name
        temp_resource_path.write_bytes(resource_bytes)
        return str(temp_resource_path)

    def get_bytes(self, resource_name: str) -> bytes:
        path_from_meipass = self._get_meipass_path(resource_name)
        if path_from_meipass is not None:
            return path_from_meipass.read_bytes()

        package_resource_path = self._get_package_path(resource_name)
        return package_resource_path.read_bytes()
