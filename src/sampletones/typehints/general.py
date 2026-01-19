import os
from collections.abc import Hashable
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel

from sampletones.constants.enums import FeatureKey

Numeric = Union[int, float, np.integer, np.floating]

Initials = Optional[Tuple[Any, ...]]
SerializedData = Dict[str, Any]
ReducedObject = Tuple[Any, Tuple[SerializedData]]
ModelHashable = Union[Hashable, BaseModel]

FeatureValue = Union[int, np.ndarray]
FeatureMap = Dict[FeatureKey, FeatureValue]

Sender = Union[int, str]
Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

Callback = Callable[..., Any]
VoidCallback = Callable[[], None]
PathCallback = Callable[[Path], None]
MessageCallback = Callable[..., str]

Pathlike = Union[str, Path]
GeneralPathlike = Union[Pathlike, os.PathLike[str]]
