import os
from collections.abc import Hashable
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, Union

import numpy as np
from pydantic import BaseModel

from sampletones import xp
from sampletones.constants.enums import FeatureKey

T = TypeVar("T")

Integer = Union[int, np.integer, xp.integer]
Float = Union[float, np.floating, xp.floating]
Numeric = Union[Integer, Float]
ArrayOrScalar = Union[Numeric, np.ndarray, xp.ndarray]

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

UnaryTransformation = Callable[[T], T]
BinaryTransformation = Callable[[T, T], T]
MultaryTransformation = Callable[..., T]
