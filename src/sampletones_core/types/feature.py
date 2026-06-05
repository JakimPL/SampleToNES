from typing import Dict, Union

import numpy as np

from sampletones_core.constants.enums import FeatureKey

FeatureValue = Union[int, np.ndarray]
FeatureMap = Dict[FeatureKey, FeatureValue]
