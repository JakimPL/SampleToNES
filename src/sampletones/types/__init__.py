import os
from collections.abc import Hashable
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel

from sampletones.constants.enums import FeatureKey

Integer = Union[int, np.integer]
Float = Union[float, np.floating]
Numeric = Union[Integer, Float]

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
