from .base import SampleToNESError


class LanguageError(SampleToNESError):
    """Base exception for interface-text errors."""


class MalformedTextKeyError(LanguageError):
    """Raised when a text key departs from the page.panel.text_type.element grammar."""


class MissingTextError(LanguageError):
    """Raised when a well-formed text key is absent from the loaded language file."""
