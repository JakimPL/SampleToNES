from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from sampletones.constants.enums import FeatureKey

Initials = Optional[Tuple[Any, ...]]
SerializedData = Dict[str, Any]
Metadata = Dict[str, Dict[str, str]]

FeatureValue = Union[int, np.ndarray]
FeatureMap = Dict[FeatureKey, FeatureValue]

Sender = Union[int, str]
