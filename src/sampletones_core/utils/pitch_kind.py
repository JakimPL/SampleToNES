from dataclasses import dataclass
from typing import Callable, Mapping

from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MIN_PITCH
from sampletones_core.utils.frequencies import (
    SANITIZED_NAME_TO_PERIOD,
    SANITIZED_NAME_TO_PITCH,
    clamp_period,
    clamp_pitch,
    period_to_name,
    pitch_to_name,
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

PERIOD_VALUE_KIND = PitchValueKind(
    minimum=0,
    maximum=MAX_PERIOD,
    clamp=clamp_period,
    to_name=period_to_name,
    sanitize=sanitize_period,
    sanitized_name_to_value=SANITIZED_NAME_TO_PERIOD,
)
