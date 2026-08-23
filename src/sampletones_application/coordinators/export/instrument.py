from pathlib import Path
from typing import Dict, Tuple

from sampletones_application.categories.elements.global_ import FileFilterElements
from sampletones_application.categories.exports import (
    EXPORT_INSTRUMENT_FILTERS,
    INSTRUMENT_EXPORT_FORMATS,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.export.instrument import InstrumentExportLogic
from sampletones_application.utils.file_dialogs.api import save_file_dialog
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import InstrumentSource
from sampletones_core.exports.scope import ExportScope


class InstrumentExportCoordinator:
    """The screen one instrument's export is asked for on, wherever the request came from.

    Every surface offering an instrument export — the Reconstructions tab's channel buttons, the
    sequencer's voice menu — raises the same dialog here, so an instrument is written the same way
    whichever of them asked. All three formats that write a single instrument are offered at once,
    which leaves choosing one to the dialog's own type selector rather than to the menu that
    reached it.
    """

    def __init__(
        self,
        export_logic: InstrumentExportLogic,
        language_manager: LanguageManager,
    ) -> None:
        self._logic = export_logic
        self._title = language_manager["reconstructions.instruments.title.export_instrument_dialog"]
        self._filter_names: Dict[ExportFormat, str] = {
            export_format: self._filter_name(language_manager, element)
            for export_format, element in EXPORT_INSTRUMENT_FILTERS.items()
        }

    def request(self, source: InstrumentSource, suggested_name: str) -> None:
        """Asks where one instrument goes, then writes it there.

        The dialog opens on the folder the last instrument landed in and suggests the instrument's
        own name, leaving the format to the type selector and to any extension typed over it.

        Args:
            source: The instrument to write, awaiting the name its destination gives it.
            suggested_name: The name the dialog opens with, which the instrument keeps unless the
                reader renames the file.
        """
        destination = save_file_dialog(
            title=self._title,
            initial_directory=self._logic.suggested_directory,
            default_filename=suggested_name,
            filters=self._filters(),
        )

        self._write(destination, source)

    @ignore_none_path
    def _write(self, destination: Path, source: InstrumentSource) -> None:
        self._logic.export(destination, source)

    def _filters(self) -> Tuple[FileFilter, ...]:
        """The types a destination may be given, one per format writing a single instrument.

        Naming each format's own type puts the programs an export can reach into the dialog's type
        selector, so the one picked there names the format the instrument is written in.
        """
        return tuple(self._filter(export_format) for export_format in INSTRUMENT_EXPORT_FORMATS)

    def _filter(self, export_format: ExportFormat) -> FileFilter:
        return FileFilter.for_extensions(
            self._filter_names[export_format],
            [self._logic.backends[export_format].extension(ExportScope.INSTRUMENT)],
        )

    @staticmethod
    def _filter_name(
        language_manager: LanguageManager,
        element: FileFilterElements,
    ) -> str:
        return language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.FILTER,
            element,
        ]
