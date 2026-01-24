from typing import Dict, Union

import numpy as np

from sampletones.constants.enums import FeatureKey

FeatureValue = Union[int, np.ndarray]
FeatureMap = Dict[FeatureKey, FeatureValue]
