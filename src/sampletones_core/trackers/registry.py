from typing import Dict

from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.bitphase import BitphaseBackend, BitphasePresetBackend
from sampletones_core.trackers.famitracker import FamiTrackerBackend
from sampletones_core.trackers.format import TrackerFormat


def build_tracker_backends() -> Dict[TrackerFormat, TrackerBackend]:
    """Builds one backend per tracker format the application can write.

    The composition root calls this once and hands the result to the components that
    offer a format choice, so a new format reaches the whole application by joining
    this mapping.

    Returns:
        Dict[TrackerFormat, TrackerBackend]: Every backend, keyed by the format it writes.
    """
    return {
        TrackerFormat.FAMITRACKER: FamiTrackerBackend(),
        TrackerFormat.BITPHASE: BitphaseBackend(),
        TrackerFormat.BITPHASE_PRESET: BitphasePresetBackend(),
    }
