from collections.abc import Hashable
from typing import Any, Dict, Optional, Tuple, TypeAlias, Union

from pydantic import BaseModel

Initials: TypeAlias = Optional[Tuple[Any, ...]]
SerializedData: TypeAlias = Dict[str, Any]
ReducedObject: TypeAlias = Tuple[Any, Tuple[SerializedData]]
ModelHashable: TypeAlias = Union[Hashable, BaseModel]
