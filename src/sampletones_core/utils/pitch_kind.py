from dataclasses import dataclass
from typing import Callable, Mapping

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MIN_PITCH, MIN_PLAYED_PITCH
from sampletones_core.features import speaks_in_periods
from sampletones_core.utils.frequencies import (
    SANITIZED_NAME_TO_PERIOD,
    SANITIZED_NAME_TO_PITCH,
    SANITIZED_NAME_TO_PLAYED_PITCH,
    clamp_period,
    clamp_pitch,
    period_to_name,
    pitch_to_name,
    played_pitch,
    sanitize_period,
    sanitize_pitch,
)


@dataclass(frozen=True)
class PitchValueKind:
    """Bundles the value semantics of a steppable NES pitch-like quantity (a channel pitch or a noise
    period): its range, how an integer is clamped into that range, how a value renders as a FamiTracker
    note name, and how typed text resolves back to a value. Both the application's UI and logic layers
    share a single instance per quantity, keeping the pitch-versus-period distinction in one place."""

    minimum: int
    maximum: int
    clamp: Callable[[int], int]
    to_name: Callable[[int], str]
    sanitize: Callable[[str], str]
    sanitized_name_to_value: Mapping[str, int]

    def from_text(self, text: str, fallback: int) -> int:
        """Resolves typed text to a value within range. An integer is clamped to the range; other text is
        treated as a note name, sanitized and looked up, returning fallback when the name is unknown."""
        try:
            return self.clamp(int(text))
        except ValueError:
            return self.sanitized_name_to_value.get(self.sanitize(text), fallback)


PITCH_VALUE_KIND = PitchValueKind(
    minimum=MIN_PITCH,
    maximum=MAX_PITCH,
    clamp=clamp_pitch,
    to_name=pitch_to_name,
    sanitize=sanitize_pitch,
    sanitized_name_to_value=SANITIZED_NAME_TO_PITCH,
)

PLAYED_PITCH_VALUE_KIND = PitchValueKind(
    minimum=MIN_PLAYED_PITCH,
    maximum=MAX_PITCH,
    clamp=played_pitch,
    to_name=pitch_to_name,
    sanitize=sanitize_pitch,
    sanitized_name_to_value=SANITIZED_NAME_TO_PLAYED_PITCH,
)

PERIOD_VALUE_KIND = PitchValueKind(
    minimum=0,
    maximum=MAX_PERIOD,
    clamp=clamp_period,
    to_name=period_to_name,
    sanitize=sanitize_period,
    sanitized_name_to_value=SANITIZED_NAME_TO_PERIOD,
)


def channel_pitch_kind(channel_name: ChannelName) -> PitchValueKind:
    """The terms a channel states its pitch-like values in.

    Args:
        channel_name: The channel being read.

    Returns:
        PitchValueKind: The noise channel's periods, or the semitones the others name.
    """
    return PERIOD_VALUE_KIND if speaks_in_periods(channel_name) else PITCH_VALUE_KIND


def note_value_kind(channel_name: ChannelName) -> PitchValueKind:
    """The terms a row's note is held to on a channel.

    A tonal channel plays every note from C-0 up, a wider range than a voice's reference may rest
    at, so a note typed into a row reaches the lowest notes the trackers write. The noise channel
    names its sixteen periods.

    Args:
        channel_name: The channel the row stands on.

    Returns:
        PitchValueKind: The noise channel's periods, or the notes the others play.
    """
    return PERIOD_VALUE_KIND if speaks_in_periods(channel_name) else PLAYED_PITCH_VALUE_KIND
