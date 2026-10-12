from importlib import metadata
from typing import Final

from sampletones_shared.application import SAMPLETONES_NAME, SAMPLETONES_PACKAGE_NAME

PROJECT_URL_FIELD: Final[str] = "Project-URL"
PROJECT_URL_SEPARATOR: Final[str] = ","
DOCUMENTATION_LABEL: Final[str] = "Documentation"


def project_address(label: str) -> str:
    """The address the installed distribution lists under ``label``, as ``[project.urls]`` names it.

    Raises:
        KeyError: If the distribution lists no address under that label.
    """
    for entry in metadata.metadata(SAMPLETONES_PACKAGE_NAME).get_all(PROJECT_URL_FIELD) or []:
        name, _, address = str(entry).partition(PROJECT_URL_SEPARATOR)
        if name.strip() == label:
            return address.strip()

    raise KeyError(f"The {SAMPLETONES_PACKAGE_NAME} distribution lists no {label} address")


SAMPLETONES_VERSION: Final[str] = metadata.version(SAMPLETONES_PACKAGE_NAME)
SAMPLETONES_NAME_VERSION: Final[str] = f"{SAMPLETONES_NAME} v{SAMPLETONES_VERSION}"
SAMPLETONES_DOCUMENTATION_ADDRESS: Final[str] = project_address(DOCUMENTATION_LABEL)
