from .base import SampleToNESWarning


class IncompleteHistogramRebinningWarning(SampleToNESWarning):
    """Warning raised when histogram rebinning results in incomplete bins."""
