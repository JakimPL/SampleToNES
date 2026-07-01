from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple, Union

from sampletones_shared.utils.validation import Location


class ConfigLoadFailureReason(Enum):
    """Domain category of a configuration load failure, decoupled from any message text."""

    LOAD_ERROR = auto()
    PARSE_ERROR = auto()
    INVALID = auto()


@dataclass(frozen=True)
class ConfigRecovered:
    """
    Records that a stored configuration was loaded after discarding incompatible values.

    Attributes:
        source_version: The version string found in the stored file, or None when the
            file predates versioned metadata.
        dropped: The raw validation locations whose stored values were discarded. They
            stay unflattened here; rendering them for display belongs to the coordinator.
    """

    source_version: Optional[str]
    dropped: Tuple[Location, ...]


@dataclass(frozen=True)
class ConfigLoadFailure:
    """
    Records that a stored configuration could not be loaded and defaults were applied.

    Attributes:
        exception: The failure that triggered the fallback to defaults.
        reason: The domain category used to pick the message the coordinator presents.
    """

    exception: Exception
    reason: ConfigLoadFailureReason


ConfigLoadOutcome = Union[ConfigRecovered, ConfigLoadFailure]
