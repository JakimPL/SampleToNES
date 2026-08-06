from enum import StrEnum, auto


class ObjectKind(StrEnum):
    LIBRARY = auto()
    RECONSTRUCTION = auto()
    PROJECT = auto()
