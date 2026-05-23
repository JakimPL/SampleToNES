from .base import SampleToNESError


class InvalidDataError(SampleToNESError):
    """Base class for invalid data errors."""


class InvalidValuesError(InvalidDataError):
    """Raised when data contains invalid values."""

    def __init__(self, message: str, validation_error: Exception) -> None:
        self.message = message
        self.validation_error = validation_error
        super().__init__(str(validation_error))

    def __str__(self) -> str:
        return f"{self.message}:\n{self.validation_error}"


class InvalidMetadataError(InvalidDataError):
    """Exception raised for invalid metadata."""


class SerializationError(InvalidDataError):
    """Raised when serialization fails."""


class DeserializationError(InvalidDataError):
    """Raised when deserialization fails."""
