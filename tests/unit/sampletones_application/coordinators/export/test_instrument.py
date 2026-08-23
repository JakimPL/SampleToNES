from pathlib import Path
from typing import Dict, Final, List, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.exports import INSTRUMENT_EXPORT_FORMATS
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.export import instrument as instrument_module
from sampletones_application.coordinators.export.instrument import (
    InstrumentExportCoordinator,
)
from sampletones_application.exports import build_export_backends
from sampletones_application.logic.export.instrument import (
    voice_instrument,
    voice_instruments,
)
from sampletones_application.paths import LANG_EN
from sampletones_core.exports.request import InstrumentSource
from sampletones_core.exports.scope import ExportScope
from sampletones_core.project.project import Project
from sampletones_core.project.voices.creation import new_instrument

REMEMBERED_DIRECTORY: Final[Path] = Path("/instruments")
SUGGESTED_NAME: Final[str] = "Lead"
DESTINATION: Final[Path] = REMEMBERED_DIRECTORY / "Lead.fti"


def _source() -> InstrumentSource:
    voice = new_instrument(SUGGESTED_NAME)
    project = Project.create()
    project.voices.append(voice)
    return voice_instrument(project, voice_instruments(voice)[0]).source


@pytest.fixture
def logic() -> MagicMock:
    mock = MagicMock()
    mock.suggested_directory = REMEMBERED_DIRECTORY
    mock.backends = build_export_backends()
    return mock


@pytest.fixture
def coordinator(logic: MagicMock) -> InstrumentExportCoordinator:
    return InstrumentExportCoordinator(logic, LanguageManager(LANG_EN))


@pytest.fixture
def confirmed(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, object]]:
    """The save dialog, answering with a destination and recording how it was opened."""
    opened: List[Dict[str, object]] = []

    def _save(**kwargs: object) -> Path:
        opened.append(kwargs)
        return DESTINATION

    monkeypatch.setattr(instrument_module, "save_file_dialog", _save)
    return opened


@pytest.fixture
def cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(instrument_module, "save_file_dialog", lambda **_kwargs: None)


class TestAskingWhereAnInstrumentGoes:
    def test_the_dialog_opens_where_the_last_instrument_landed(
        self,
        coordinator: InstrumentExportCoordinator,
        confirmed: List[Dict[str, object]],
    ) -> None:
        coordinator.request(_source(), SUGGESTED_NAME)

        assert confirmed[0]["initial_directory"] == REMEMBERED_DIRECTORY

    def test_the_instrument_names_the_file_it_is_offered_as(
        self,
        coordinator: InstrumentExportCoordinator,
        confirmed: List[Dict[str, object]],
    ) -> None:
        coordinator.request(_source(), SUGGESTED_NAME)

        assert confirmed[0]["default_filename"] == SUGGESTED_NAME

    def test_every_format_writing_one_instrument_is_offered_at_once(
        self,
        coordinator: InstrumentExportCoordinator,
        confirmed: List[Dict[str, object]],
    ) -> None:
        """Choosing the format is the dialog's own type selector, not the menu that reached it."""
        coordinator.request(_source(), SUGGESTED_NAME)

        filters = confirmed[0]["filters"]
        assert isinstance(filters, tuple)
        assert len(filters) == len(INSTRUMENT_EXPORT_FORMATS)

    def test_each_type_carries_the_extension_its_format_writes(
        self,
        coordinator: InstrumentExportCoordinator,
        logic: MagicMock,
        confirmed: List[Dict[str, object]],
    ) -> None:
        coordinator.request(_source(), SUGGESTED_NAME)

        filters = confirmed[0]["filters"]
        assert isinstance(filters, tuple)
        offered: Tuple[str, ...] = tuple(pattern for file_filter in filters for pattern in file_filter.patterns)
        for export_format in INSTRUMENT_EXPORT_FORMATS:
            extension = logic.backends[export_format].extension(ExportScope.INSTRUMENT)
            assert any(pattern.endswith(extension) for pattern in offered)

    def test_each_type_is_named_after_the_program_that_reads_it(
        self,
        coordinator: InstrumentExportCoordinator,
        confirmed: List[Dict[str, object]],
    ) -> None:
        coordinator.request(_source(), SUGGESTED_NAME)

        filters = confirmed[0]["filters"]
        assert isinstance(filters, tuple)
        assert len({file_filter.name for file_filter in filters}) == len(INSTRUMENT_EXPORT_FORMATS)


class TestWritingWhatWasConfirmed:
    def test_the_destination_reaches_the_write(
        self,
        coordinator: InstrumentExportCoordinator,
        logic: MagicMock,
        confirmed: List[Dict[str, object]],
    ) -> None:
        source = _source()

        coordinator.request(source, SUGGESTED_NAME)

        logic.export.assert_called_once_with(DESTINATION, source)

    def test_a_cancelled_dialog_writes_nothing(
        self,
        coordinator: InstrumentExportCoordinator,
        logic: MagicMock,
        cancelled: None,
    ) -> None:
        coordinator.request(_source(), SUGGESTED_NAME)

        logic.export.assert_not_called()
