from dataclasses import dataclass
from typing import Union

from sampletones_application.services.result import (
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class RegeneratedInstrument:
    """A reconstruction with one channel rebuilt from the envelopes the regeneration was handed.

    The caller keeps what it asked for, so the result carries the rebuilt document alone.

    Attributes:
        reconstruction: The fresh reconstruction carrying the rebuilt channel.
    """

    reconstruction: Reconstruction


RegenerationResult = Union[
    ServiceSuccess[RegeneratedInstrument],
    ServiceError,
]
