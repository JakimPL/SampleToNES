from typing import Annotated, Any, Union

from pydantic import BeforeValidator, Field, StrictFloat, StrictInt

from sampletones_core.constants.general import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from sampletones_core.utils.frequencies import pitch_to_frequency


def _require_hertz(value: Any) -> Any:
    """
    Keep the Hz branch of the frequency union float-only.

    Pydantic accepts integers as float input even in strict mode, so integers
    must be turned away here for the union to discriminate on the Python type:
    an integer is a MIDI pitch and belongs to the pitch branch alone.

    Raises:
        ValueError: If the value is an integer.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        raise ValueError("An integer frequency specification is a MIDI pitch and must lie in the pitch range")

    return value


def resolve_frequency(frequency: Union[int, float]) -> float:
    """
    Resolve a frequency specification to Hz.

    An integer is a MIDI pitch converted through equal temperament, so musically
    oriented configurations stay readable in note numbers; a float is already a
    frequency in Hz.

    Args:
        frequency: MIDI pitch (int) or frequency in Hz (float).

    Returns:
        The frequency in Hz.

    Raises:
        ValueError: If an integer pitch lies outside the range 24-127.
    """
    match frequency:
        case int():
            return pitch_to_frequency(frequency)
        case float():
            return frequency


PitchSpec = Annotated[StrictInt, Field(ge=LIMIT_MIN_PITCH, le=LIMIT_MAX_PITCH)]
HertzSpec = Annotated[StrictFloat, Field(gt=0.0), BeforeValidator(_require_hertz)]
FrequencySpec = Union[PitchSpec, HertzSpec]
