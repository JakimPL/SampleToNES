from functools import lru_cache
from pathlib import Path
from typing import Dict, Final, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from sampletones_application.utils.file_dialogs.backends.portal.client import FileChooserClient
from sampletones_application.utils.file_dialogs.backends.portal.response import ChooserResult
from sampletones_application.utils.file_dialogs.backends.portal.variant import (
    BOOLEAN_SIGNATURE,
    BYTES_SIGNATURE,
    STRING_SIGNATURE,
    Variant,
)
from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter

OPEN_FILE_METHOD: Final[str] = "OpenFile"
SAVE_FILE_METHOD: Final[str] = "SaveFile"

FILTERS_OPTION: Final[str] = "filters"
CURRENT_FILTER_OPTION: Final[str] = "current_filter"
CURRENT_NAME_OPTION: Final[str] = "current_name"
CURRENT_FOLDER_OPTION: Final[str] = "current_folder"
DIRECTORY_OPTION: Final[str] = "directory"

FILTER_SIGNATURE: Final[str] = "(sa(us))"
FILTERS_SIGNATURE: Final[str] = f"a{FILTER_SIGNATURE}"

GLOB_PATTERN: Final[int] = 0
"""The portal's kind for a filter pattern written as a shell glob."""

FILE_SCHEME: Final[str] = "file"
PATH_TERMINATOR: Final[bytes] = b"\0"

MINIMUM_FILE_CHOOSER_VERSION: Final[int] = 3
"""The version reporting the chosen type and accepting a folder to open in."""

PortalFilter = Tuple[str, List[Tuple[int, str]]]


class PortalBackend:
    """
    File dialogs opened through the XDG desktop portal.

    The portal hands each request to the desktop's own file chooser, so a dialog looks and
    behaves as the rest of the desktop does. Every offered type reaches the file-type selector
    as its own entry and the response names the entry the user left it on, which is what lets a
    save settle its extension from the type that was picked rather than the name that was typed.
    """

    def __init__(self, client: FileChooserClient) -> None:
        self._client = client

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[Path]:
        result = self._client.call(
            method=OPEN_FILE_METHOD,
            title=title,
            options=self._open_options(
                initial_directory,
                filters,
            ),
        )
        return self._chosen_path(result)

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[SaveDestination]:
        result = self._client.call(
            method=SAVE_FILE_METHOD,
            title=title,
            options=self._save_options(
                initial_directory,
                suggested_name,
                filters,
            ),
        )
        path = self._chosen_path(result)
        if result is None or path is None:
            return None

        return SaveDestination(
            path=path,
            file_type=self._reported_type(
                result,
                filters,
            ),
        )

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        result = self._client.call(
            method=OPEN_FILE_METHOD,
            title=title,
            options=self._directory_options(initial_directory),
        )
        return self._chosen_path(result)

    @classmethod
    def _open_options(
        cls,
        initial_directory: Optional[Path],
        filters: Tuple[FileFilter, ...],
    ) -> Dict[str, Variant]:
        return {
            **cls._folder_option(initial_directory),
            **cls._filter_options(filters),
        }

    @classmethod
    def _save_options(
        cls,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Dict[str, Variant]:
        options: Dict[str, Variant] = {
            **cls._folder_option(initial_directory),
            **cls._filter_options(filters),
        }
        if suggested_name:
            options[CURRENT_NAME_OPTION] = (STRING_SIGNATURE, suggested_name)

        return options

    @classmethod
    def _directory_options(
        cls,
        initial_directory: Optional[Path],
    ) -> Dict[str, Variant]:
        return {
            **cls._folder_option(initial_directory),
            DIRECTORY_OPTION: (BOOLEAN_SIGNATURE, True),
        }

    @staticmethod
    def _folder_option(initial_directory: Optional[Path]) -> Dict[str, Variant]:
        """The folder the dialog opens in, as the NUL-terminated byte string the portal reads."""
        if initial_directory is None:
            return {}

        encoded = str(initial_directory).encode() + PATH_TERMINATOR
        return {CURRENT_FOLDER_OPTION: (BYTES_SIGNATURE, encoded)}

    @classmethod
    def _filter_options(
        cls,
        filters: Tuple[FileFilter, ...],
    ) -> Dict[str, Variant]:
        """
        The types the selector lists, and the one it opens on.

        Naming the first type as the current one opens the dialog on the type a caller offers first,
        matching the extension a suggested name carries.
        """
        if not filters:
            return {}

        listed = [cls._portal_filter(file_filter) for file_filter in filters]
        return {
            FILTERS_OPTION: (FILTERS_SIGNATURE, listed),
            CURRENT_FILTER_OPTION: (FILTER_SIGNATURE, listed[0]),
        }

    @staticmethod
    def _portal_filter(file_filter: FileFilter) -> PortalFilter:
        patterns = [(GLOB_PATTERN, pattern) for pattern in file_filter.patterns]
        return (file_filter.label, patterns)

    @staticmethod
    def _reported_type(
        result: ChooserResult,
        filters: Tuple[FileFilter, ...],
    ) -> Optional[FileFilter]:
        """The offered type whose label the dialog reported, for a portal implementation reporting one."""
        for file_filter in filters:
            if file_filter.label == result.filter_label:
                return file_filter

        return None

    @staticmethod
    def _chosen_path(result: Optional[ChooserResult]) -> Optional[Path]:
        """The local path the dialog answered with, for the ``file`` locations the portal hands back."""
        if result is None or not result.uris:
            return None

        location = urlparse(result.uris[0])
        if location.scheme != FILE_SCHEME:
            return None

        return Path(unquote(location.path))


@lru_cache(maxsize=1)
def portal_backend() -> Optional[PortalBackend]:
    """
    Returns portal-backed dialogs once a portal implementing ``FileChooser`` answers on the bus.

    The answer holds for the life of the process, since a desktop either runs a portal or leaves
    dialogs to another backend, so every dialog after the first opens with no further round trip.
    """
    client = FileChooserClient()
    version = client.version()
    if version is None or version < MINIMUM_FILE_CHOOSER_VERSION:
        return None

    return PortalBackend(client)
