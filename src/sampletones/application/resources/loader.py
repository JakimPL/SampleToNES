import sys
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Union

from sampletones_shared.types.path import Pathlike


class ResourceLoader:
    def __init__(self, resource_directory: Pathlike) -> None:
        self.resource_directory = Path(resource_directory)

    def _get_package_path(self, resource_name: str) -> Union[Path, Traversable]:
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined] # pylint: disable=protected-access
            resource_type = self.resource_directory.name
            return base_path / "assets" / resource_type / resource_name

        package_name = f"sampletones_assets.{self.resource_directory.name}"
        return files(package_name).joinpath(resource_name)

    def get_path(self, resource_name: str) -> str:
        resource_path = self._get_package_path(resource_name)

        if isinstance(resource_path, Path):
            if not resource_path.exists():
                raise FileNotFoundError(f"Resource not found: '{resource_path}'")
        else:
            try:
                resource_path.read_bytes()
            except FileNotFoundError as exception:
                raise FileNotFoundError(f"Resource not found: '{resource_path}'") from exception

        return str(resource_path)

    def get_bytes(self, resource_name: str) -> bytes:
        resource_path = self._get_package_path(resource_name)
        return resource_path.read_bytes()
