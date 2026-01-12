from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

import numpy as np

from sampletones.constants.enums import FeatureKey

Numeric = Union[int, float, np.floating, np.integer]

Initials = Optional[Tuple[Any, ...]]
SerializedData = Dict[str, Any]
ReducedObject = Tuple[Any, Tuple[SerializedData]]

FeatureValue = Union[int, np.ndarray]
FeatureMap = Dict[FeatureKey, FeatureValue]

Sender = Union[int, str]
Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

Callback = Callable[..., Any]
VoidCallback = Callable[[], None]
PathCallback = Callable[[Path], None]
MessageCallback = Callable[..., str]

Pathlike = Union[str, Path]
