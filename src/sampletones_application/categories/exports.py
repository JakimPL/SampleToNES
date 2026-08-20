from dataclasses import dataclass
from typing import Dict, Final, Tuple

from sampletones_application.categories.elements.global_ import (
    FileFilterElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
    MenuElements,
)
from sampletones_core.exports.format import ExportFormat


@dataclass(frozen=True)
class ExportProjectElements:
    """Which texts one export format's project export reads.

    Every format names its own file kind, so the dialog that picks a destination and the
    one that reports the outcome speak in the words of the program that reads the file.

    Attributes:
        dialog_title: Title of the dialog the destination is picked in.
        filter_name: Name of the file filter the dialog offers.
        exported_message: Shown when the project reaches its file.
        export_failed_message: Shown when the export fails.
    """

    dialog_title: GlobalDialogTitleElements
    filter_name: FileFilterElements
    exported_message: GlobalMessageElements
    export_failed_message: GlobalMessageElements


EXPORT_PROJECT_ELEMENTS: Final[Dict[ExportFormat, ExportProjectElements]] = {
    ExportFormat.FAMITRACKER: ExportProjectElements(
        dialog_title=GlobalDialogTitleElements.EXPORT_MODULE,
        filter_name=FileFilterElements.MODULE,
        exported_message=GlobalMessageElements.PROJECT_EXPORTED_SUCCESSFULLY,
        export_failed_message=GlobalMessageElements.PROJECT_EXPORT_FAILED,
    ),
    ExportFormat.BITPHASE: ExportProjectElements(
        dialog_title=GlobalDialogTitleElements.EXPORT_BITPHASE_PROJECT,
        filter_name=FileFilterElements.BITPHASE_PROJECT,
        exported_message=GlobalMessageElements.BITPHASE_PROJECT_EXPORTED_SUCCESSFULLY,
        export_failed_message=GlobalMessageElements.BITPHASE_PROJECT_EXPORT_FAILED,
    ),
}

EXPORT_PROJECT_MENU_LABELS: Final[Dict[ExportFormat, MenuElements]] = {
    ExportFormat.FAMITRACKER: MenuElements.ITEM_FILE_EXPORT_FAMITRACKER,
    ExportFormat.BITPHASE: MenuElements.ITEM_FILE_EXPORT_BITPHASE,
}

INSTRUMENT_EXPORT_FORMATS: Final[Tuple[ExportFormat, ...]] = (
    ExportFormat.FAMITRACKER,
    ExportFormat.BITPHASE_PRESET,
)

EXPORT_INSTRUMENT_FILTERS: Final[Dict[ExportFormat, FileFilterElements]] = {
    ExportFormat.FAMITRACKER: FileFilterElements.FAMITRACKER_INSTRUMENT,
    ExportFormat.BITPHASE_PRESET: FileFilterElements.BITPHASE_PRESET,
}

EXPORT_SAMPLE_MENU_LABELS: Final[Dict[ExportFormat, MenuElements]] = {
    ExportFormat.FAMITRACKER: MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_FAMITRACKER,
    ExportFormat.BITPHASE_PRESET: MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_BITPHASE_PRESET,
}
