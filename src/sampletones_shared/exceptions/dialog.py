from .base import SampleToNESError


class FileDialogUnavailableError(SampleToNESError):
    """Raised when the environment provides no usable file-dialog backend, naming the packages that supply one."""
