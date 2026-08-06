from pathlib import Path
from typing import Dict, Final, List, Optional, Tuple

import pytest

from sampletones_application.utils.file_dialogs.backends.portal.backend import (
    CURRENT_FILTER_OPTION,
    CURRENT_FOLDER_OPTION,
    CURRENT_NAME_OPTION,
    DIRECTORY_OPTION,
    FILTERS_OPTION,
    MINIMUM_FILE_CHOOSER_VERSION,
    PortalBackend,
)
from sampletones_application.utils.file_dialogs.backends.portal.response import ChooserResult
from sampletones_application.utils.file_dialogs.backends.portal.variant import Variant
from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter

FAMITRACKER_FILTER: Final[FileFilter] = FileFilter(name="FamiTracker instrument", patterns=("*.fti",))
PRESET_FILTER: Final[FileFilter] = FileFilter(name="Bitphase instrument preset", patterns=("*.json",))
INSTRUMENT_FILTERS: Final[Tuple[FileFilter, ...]] = (FAMITRACKER_FILTER, PRESET_FILTER)

HOME: Final[Path] = Path("/home/user")


class FakeClient:
    """A portal answering with one prepared result, recording what it was asked to show."""

    def __init__(
        self,
        result: Optional[ChooserResult],
        version: Optional[int] = MINIMUM_FILE_CHOOSER_VERSION,
    ) -> None:
        self._result = result
        self._version = version
        self.calls: List[Tuple[str, str, Dict[str, Variant]]] = []

    def version(self) -> Optional[int]:
        return self._version

    def call(
        self,
        *,
        method: str,
        title: str,
        options: Dict[str, Variant],
    ) -> Optional[ChooserResult]:
        self.calls.append((method, title, options))
        return self._result


def _saved(
    uri: str,
    label: Optional[str],
) -> ChooserResult:
    return ChooserResult(uris=(uri,), filter_label=label)


class TestPortalBackendSave:
    def test_options_carry_the_types_the_name_and_the_folder(self) -> None:
        client = FakeClient(_saved("file:///home/user/kick.fti", FAMITRACKER_FILTER.label))
        backend = PortalBackend(client)

        backend.save_file(
            title="Export instrument",
            initial_directory=HOME,
            suggested_name="Kick (pulse1)",
            filters=INSTRUMENT_FILTERS,
        )

        method, title, options = client.calls[0]
        assert (method, title) == ("SaveFile", "Export instrument")
        assert options[FILTERS_OPTION] == (
            "a(sa(us))",
            [
                ("FamiTracker instrument (*.fti)", [(0, "*.fti")]),
                ("Bitphase instrument preset (*.json)", [(0, "*.json")]),
            ],
        )
        assert options[CURRENT_NAME_OPTION] == ("s", "Kick (pulse1)")
        assert options[CURRENT_FOLDER_OPTION] == ("ay", b"/home/user\x00")

    def test_the_dialog_opens_on_the_first_offered_type(self) -> None:
        client = FakeClient(_saved("file:///home/user/kick.fti", FAMITRACKER_FILTER.label))
        backend = PortalBackend(client)

        backend.save_file(
            title="Export instrument",
            initial_directory=None,
            suggested_name=None,
            filters=INSTRUMENT_FILTERS,
        )

        options = client.calls[0][2]
        assert options[CURRENT_FILTER_OPTION] == ("(sa(us))", ("FamiTracker instrument (*.fti)", [(0, "*.fti")]))
        assert CURRENT_NAME_OPTION not in options
        assert CURRENT_FOLDER_OPTION not in options

    def test_the_reported_label_names_the_offered_type(self) -> None:
        client = FakeClient(_saved("file:///home/user/kick", PRESET_FILTER.label))
        backend = PortalBackend(client)

        destination = backend.save_file(
            title="Export instrument",
            initial_directory=HOME,
            suggested_name="kick",
            filters=INSTRUMENT_FILTERS,
        )

        assert destination == SaveDestination(path=Path("/home/user/kick"), file_type=PRESET_FILTER)

    def test_an_unreported_type_leaves_the_destination_typeless(self) -> None:
        client = FakeClient(_saved("file:///home/user/kick.fti", None))
        backend = PortalBackend(client)

        destination = backend.save_file(
            title="Export instrument",
            initial_directory=HOME,
            suggested_name="kick",
            filters=INSTRUMENT_FILTERS,
        )

        assert destination == SaveDestination(path=Path("/home/user/kick.fti"), file_type=None)

    def test_a_dismissed_dialog_answers_with_nothing(self) -> None:
        client = FakeClient(None)
        backend = PortalBackend(client)

        destination = backend.save_file(
            title="Export instrument",
            initial_directory=HOME,
            suggested_name="kick",
            filters=INSTRUMENT_FILTERS,
        )

        assert destination is None


class TestPortalBackendOpen:
    def test_an_escaped_uri_reads_as_the_path_it_names(self) -> None:
        client = FakeClient(_saved("file:///home/user/Kick%20%28pulse1%29.fti", FAMITRACKER_FILTER.label))
        backend = PortalBackend(client)

        filepath = backend.open_file(
            title="Open instrument",
            initial_directory=HOME,
            filters=INSTRUMENT_FILTERS,
        )

        assert filepath == Path("/home/user/Kick (pulse1).fti")
        assert client.calls[0][0] == "OpenFile"

    def test_a_location_outside_the_file_system_answers_with_nothing(self) -> None:
        client = FakeClient(_saved("https://example.invalid/kick.fti", None))
        backend = PortalBackend(client)

        filepath = backend.open_file(
            title="Open instrument",
            initial_directory=HOME,
            filters=INSTRUMENT_FILTERS,
        )

        assert filepath is None

    def test_no_offered_types_leaves_the_selector_out(self) -> None:
        client = FakeClient(_saved("file:///home/user/kick.fti", None))
        backend = PortalBackend(client)

        backend.open_file(
            title="Open instrument",
            initial_directory=HOME,
            filters=(),
        )

        options = client.calls[0][2]
        assert FILTERS_OPTION not in options
        assert CURRENT_FILTER_OPTION not in options


class TestPortalBackendSelectDirectory:
    def test_the_dialog_is_asked_for_a_folder(self) -> None:
        client = FakeClient(_saved("file:///home/user/instruments", None))
        backend = PortalBackend(client)

        directory = backend.select_directory(title="Choose folder", initial_directory=HOME)

        method, _title, options = client.calls[0]
        assert directory == Path("/home/user/instruments")
        assert method == "OpenFile"
        assert options[DIRECTORY_OPTION] == ("b", True)


class TestPortalAvailability:
    @pytest.mark.parametrize("version", [None, MINIMUM_FILE_CHOOSER_VERSION - 1])
    def test_a_portal_below_the_needed_version_leaves_dialogs_to_another_backend(
        self,
        version: Optional[int],
    ) -> None:
        from sampletones_application.utils.file_dialogs.backends.portal import backend as backend_module

        client = FakeClient(None, version=version)
        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr(backend_module, "FileChooserClient", lambda: client)
            backend_module.portal_backend.cache_clear()
            try:
                assert backend_module.portal_backend() is None
            finally:
                backend_module.portal_backend.cache_clear()
