from .base import SampleToNESError


class MetadataError(SampleToNESError):
    """Exception raised for errors in the metadata validation."""

    pass


class InvalidMetadataError(MetadataError):
    """Exception raised for invalid metadata."""

    pass
