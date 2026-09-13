from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.types.path import Pathlike

ASSETS_PACKAGE: Final[str] = "sampletones_assets"


class ResourceLoader:
    """Reads the files of one directory of the assets package, where the package lies in every copy."""

    def __init__(self, resource_directory: Pathlike) -> None:
        self.resource_directory = Path(resource_directory)

    def _get_package_path(self, resource_name: str) -> Path:
        package = f"{ASSETS_PACKAGE}.{self.resource_directory.name}"
        return package_directory(package) / resource_name

    def get_path(self, resource_name: str) -> str:
        """The resource's location, which a widget loading it by path reads.

        Raises:
            FileNotFoundError: If the directory holds no file of that name.
        """
        resource_path = self._get_package_path(resource_name)
        if not resource_path.is_file():
            raise FileNotFoundError(f"Resource not found: '{resource_path}'")

        return str(resource_path)

    def get_bytes(self, resource_name: str) -> bytes:
        return self._get_package_path(resource_name).read_bytes()
