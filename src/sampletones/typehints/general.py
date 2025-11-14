from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from sampletones.constants.enums import FeatureKey

Initials = Optional[Tuple[Any, ...]]
SerializedData = Dict[str, Any]

FeatureValue = Union[int, np.ndarray]
FeatureMap = Dict[FeatureKey, FeatureValue]

Sender = Union[int, str]
