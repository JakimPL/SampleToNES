from pydantic import ValidationError

from .base import SampleToNESError


class InvalidValuesError(SampleToNESError):
    """Raised when data contains invalid values."""

    def __init__(self, message: str, validation_error: ValidationError):
        self.message = message
        self.validation_error = validation_error
        super().__init__(str(validation_error))

    def __str__(self):
        base_message = super().__str__()
        validation_message = f"{self.message}:\n{self.validation_error}"
        return f"{base_message}\n{validation_message}"
