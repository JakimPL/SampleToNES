from .base import SampleToNESError


class InvalidValuesError(SampleToNESError):
    """Raised when data contains invalid values."""

    def __init__(self, message: str, validation_error: Exception) -> None:
        self.message = message
        self.validation_error = validation_error
        super().__init__(str(validation_error))

    def __str__(self) -> str:
        return f"{self.message}:\n{self.validation_error}"
