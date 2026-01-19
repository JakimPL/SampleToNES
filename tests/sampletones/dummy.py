from typing import Any, List

from pydantic import BaseModel, ConfigDict


class ValueObject:
    """
    Mutable hashable object.
    """

    def __init__(self, value: int) -> None:
        self.value = value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValueObject):
            return False

        return self.value == other.value


class CollisionObject:
    """
    Mutable hashable object that forces hash collisions.
    """

    def __init__(self, value: int) -> None:
        self.value = value

    def __hash__(self) -> int:
        return 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CollisionObject):
            return False

        return self.value == other.value


class ValueModel(BaseModel):
    """
    Simple Pydantic model.
    """

    value: int


class SimpleModel(BaseModel):
    """
    A mutable Pydantic model with two primitive fields.
    """

    value: int
    name: str


class ValueFrozenModel(BaseModel):
    """
    Immutable hashable Pydantic model.
    """

    model_config = ConfigDict(frozen=True)

    value: int


class NonSerializableModel(BaseModel):
    """
    Pydantic model with non-serializable field.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    data: Any


class NestedModel(BaseModel):
    """
    Pydantic model containing another model and a list.
    """

    simple: SimpleModel
    items: List[int]
