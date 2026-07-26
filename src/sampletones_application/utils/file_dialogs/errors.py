from sampletones_shared.exceptions import SampleToNESError


class FileDialogUnavailableError(SampleToNESError):
    """Raised when the environment offers no file-dialog backend, naming the packages that provide one."""
