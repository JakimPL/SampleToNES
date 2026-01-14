class ValueObject:
    def __init__(self, value: int) -> None:
        self.value = value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValueObject):
            return False
        return self.value == other.value


class CollisionObject:
    def __init__(self, value: int) -> None:
        self.value = value

    def __hash__(self) -> int:
        return 0  # Force hash collision

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CollisionObject):
            return False

        return self.value == other.value
