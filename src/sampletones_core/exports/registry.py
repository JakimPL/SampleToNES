from typing import Dict

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.implementation.bitphase import BitphaseBackend, BitphasePresetBackend
from sampletones_core.exports.implementation.famitracker import FamiTrackerBackend


def build_tracker_backends() -> Dict[ExportFormat, ExportBackend]:
    """Builds one backend per tracker format the reconstruction engine writes.

    The composition root calls this once and hands the result to the components that
    offer a format choice, so a new tracker format reaches the whole application by
    joining this mapping. A format whose backend stands above the engine — the console
    player's own — is registered beside these by the composition root itself.

    Returns:
        Dict[ExportFormat, ExportBackend]: Every tracker backend, keyed by the format it writes.
    """
    return {
        ExportFormat.FAMITRACKER: FamiTrackerBackend(),
        ExportFormat.BITPHASE: BitphaseBackend(),
        ExportFormat.BITPHASE_PRESET: BitphasePresetBackend(),
    }
