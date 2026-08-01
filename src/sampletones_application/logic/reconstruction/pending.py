from dataclasses import dataclass

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.trackers.format import TrackerFormat


@dataclass(frozen=True)
class PendingInstrumentExport:
    """The generator slice and target format awaiting a destination from the file dialog.

    The user picks what to export before picking where it goes, so the choice is held
    here until the dialog answers with a path.

    Attributes:
        generator: The slice the export writes.
        tracker_format: The format the slice is written in.
    """

    generator: GeneratorName
    tracker_format: TrackerFormat
