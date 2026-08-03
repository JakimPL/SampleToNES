from dataclasses import dataclass
from typing import Dict, Final, Tuple

from sampletones_application.categories.elements.global_ import (
    FileFilterElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
    MenuElements,
)
from sampletones_core.trackers.format import TrackerFormat


@dataclass(frozen=True)
class TrackerProjectElements:
    """Which texts one tracker format's project export reads.

    Every format names its own file kind, so the dialog that picks a destination and the
    one that reports the outcome speak in the words of the tracker that reads the file.

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


TRACKER_PROJECT_ELEMENTS: Final[Dict[TrackerFormat, TrackerProjectElements]] = {
    TrackerFormat.FAMITRACKER: TrackerProjectElements(
        dialog_title=GlobalDialogTitleElements.EXPORT_MODULE,
        filter_name=FileFilterElements.MODULE,
        exported_message=GlobalMessageElements.PROJECT_EXPORTED_SUCCESSFULLY,
        export_failed_message=GlobalMessageElements.PROJECT_EXPORT_FAILED,
    ),
    TrackerFormat.BITPHASE: TrackerProjectElements(
        dialog_title=GlobalDialogTitleElements.EXPORT_BITPHASE_PROJECT,
        filter_name=FileFilterElements.BITPHASE_PROJECT,
        exported_message=GlobalMessageElements.BITPHASE_PROJECT_EXPORTED_SUCCESSFULLY,
        export_failed_message=GlobalMessageElements.BITPHASE_PROJECT_EXPORT_FAILED,
    ),
}

TRACKER_PROJECT_MENU_LABELS: Final[Dict[TrackerFormat, MenuElements]] = {
    TrackerFormat.FAMITRACKER: MenuElements.ITEM_FILE_EXPORT_FAMITRACKER,
    TrackerFormat.BITPHASE: MenuElements.ITEM_FILE_EXPORT_BITPHASE,
}

INSTRUMENT_EXPORT_FORMATS: Final[Tuple[TrackerFormat, ...]] = (
    TrackerFormat.FAMITRACKER,
    TrackerFormat.BITPHASE_PRESET,
)
"""The formats an instrument export offers, in the order they are listed.

Both write one file per generator slice, which is what exporting instruments produces. A
Bitphase project holds a whole composition, so it is written through the project export.
"""

TRACKER_INSTRUMENT_FILTERS: Final[Dict[TrackerFormat, FileFilterElements]] = {
    TrackerFormat.FAMITRACKER: FileFilterElements.FAMITRACKER_INSTRUMENT,
    TrackerFormat.BITPHASE_PRESET: FileFilterElements.BITPHASE_PRESET,
}
"""The file type each instrument-export format is offered under, keyed by its format."""

TRACKER_SAMPLE_MENU_LABELS: Final[Dict[TrackerFormat, MenuElements]] = {
    TrackerFormat.FAMITRACKER: MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_FAMITRACKER,
    TrackerFormat.BITPHASE_PRESET: MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS_BITPHASE_PRESET,
}
