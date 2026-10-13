from .base import SampleToNESError, SampleToNESWarning


class CuPyUnavailableWarning(SampleToNESWarning):
    """Warning raised when the process computes on NumPy because CuPy is missing or finds no graphics card."""


class GPUBackendError(SampleToNESError):
    """Raised when a build held to the GPU backend computes on the CPU, or the card answers wrong."""
