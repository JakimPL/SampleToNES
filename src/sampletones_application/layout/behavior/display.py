from typing import Tuple

from pydantic import BaseModel, Field, field_validator

from sampletones_shared.display import Resolution


class DisplayBehavior(BaseModel, extra="forbid", frozen=True):
    """What the display settings offer: the window sizes and the frame rates a user picks from,
    and how long a window mode nobody confirms stays on screen.

    Each list is offered in the order it is written, so a combo shows the entries as the file
    declares them and a selection maps to its position. A list holds each entry once, in
    ascending order, which the load checks so a mistake in the file surfaces at startup.
    """

    resolutions: Tuple[Resolution, ...] = Field(min_length=1)
    frame_rates: Tuple[int, ...] = Field(min_length=1)
    revert_countdown_seconds: float = Field(gt=0.0)

    @field_validator("resolutions")
    @classmethod
    def _validate_resolutions(
        cls,
        resolutions: Tuple[Resolution, ...],
    ) -> Tuple[Resolution, ...]:
        sizes = [(resolution.width, resolution.height) for resolution in resolutions]
        if sizes != sorted(set(sizes)):
            raise ValueError("Offered resolutions must be listed once each, in ascending order")

        return resolutions

    @field_validator("frame_rates")
    @classmethod
    def _validate_frame_rates(
        cls,
        frame_rates: Tuple[int, ...],
    ) -> Tuple[int, ...]:
        if list(frame_rates) != sorted(set(frame_rates)):
            raise ValueError("Offered frame rates must be listed once each, in ascending order")

        return frame_rates
