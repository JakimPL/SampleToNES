from .base import SampleToNESError, SampleToNESWarning


class CuPyNotInstalledWarning(SampleToNESWarning):
    """Warning raised when CuPy is not installed."""


class GPUBackendError(SampleToNESError):
    """Raised when a build held to the GPU backend computes on the CPU, or the card answers wrong."""
