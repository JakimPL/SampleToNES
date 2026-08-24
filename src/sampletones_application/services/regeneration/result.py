from dataclasses import dataclass
from typing import Union

from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class RegeneratedInstrument:
    """A regeneration result paired with the generator and feature that changed.

    Carrying the request context alongside the fresh reconstruction lets the
    history record which channel and feature an edit touched.
    """

    reconstruction: Reconstruction
    channel_name: ChannelName
    feature_key: FeatureKey


RegenerationResult = Union[
    ServiceSuccess[RegeneratedInstrument],
    ServiceError,
    ServiceCancelled,
]
