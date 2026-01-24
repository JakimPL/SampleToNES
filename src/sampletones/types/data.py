from collections.abc import Hashable
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import BaseModel

Initials = Optional[Tuple[Any, ...]]
SerializedData = Dict[str, Any]
ReducedObject = Tuple[Any, Tuple[SerializedData]]
ModelHashable = Union[Hashable, BaseModel]
