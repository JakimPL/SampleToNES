from enum import StrEnum


class ViolationKind(StrEnum):
    """A use of the device that no correct playback makes, which the fake device records as it happens."""

    OVERLAPPING_OPEN = "a stream opened while another was open"
    WRITE_AFTER_CLOSE = "a write to a closed stream"
    DRAIN_AFTER_CLOSE = "a drain of a closed stream"
    CLOSE_TWICE = "a stream closed twice"
    CLOSE_DURING_WRITE = "a stream closed from another thread while a write was in progress"
    TERMINATE_WITH_OPEN_STREAM = "the backend terminated with a stream still open"
    USE_AFTER_TERMINATE = "a call to a terminated backend"
