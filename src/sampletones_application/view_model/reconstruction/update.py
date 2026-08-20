from typing import NamedTuple

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.types.feature import FeatureValue


class ReconstructionUpdate(NamedTuple):
    channel_name: ChannelName
    feature_key: FeatureKey
    data: FeatureValue
