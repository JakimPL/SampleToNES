from typing import Dict, Iterable, Self, Tuple, TypeAlias, Union

from pydantic import BaseModel, Field, computed_field, model_validator

RawVersion: TypeAlias = Union[str, Iterable[int]]


class Version(BaseModel, frozen=True):
    major: int = Field(ge=0)
    minor: int = Field(ge=0)
    patch: int = Field(ge=0)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return str(self)

    def __le__(self, other: Self) -> bool:
        return self.tuple <= other.tuple

    def __getitem__(self, key: int) -> int:
        return self.tuple[key]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tuple(self) -> Tuple[int, int, int]:
        return self.major, self.minor, self.patch

    @model_validator(mode="before")
    @classmethod
    def parse_string(cls, value: RawVersion) -> Dict[str, int]:
        if not isinstance(value, str) and not isinstance(value, tuple):
            raise TypeError(f"Expected a tuple or a string, got {type(value)}")

        if isinstance(value, str):
            parts = tuple(filter(bool, value.split(".")))
        else:
            parts = tuple(value)

        if not 1 <= len(parts) <= 3:
            raise ValueError("Version must have 1-3 components")

        try:
            numbers = list(map(int, parts))
        except ValueError as exception:
            raise ValueError("Version components must be integers") from exception

        numbers.extend([0] * (3 - len(numbers)))

        return {
            "major": numbers[0],
            "minor": numbers[1],
            "patch": numbers[2],
        }


def _split_version(version: RawVersion) -> Version:
    """
    Splits a dotted version string into its integer components.

    Args:
        version (RawVersion): A dotted version string such as ``1.4.0``,
            or a tuple of integers such as ``(1, 4, 0)``.

    Returns:
        Version: The version object.

    Raises:
        SystemError: If input raw version object is not valid.
    """
    try:
        return Version.model_validate(version)
    except ValueError as exception:
        raise SystemError(f"Invalid version format: {exception}") from exception


def compare_versions(
    version1: Union[Version, RawVersion],
    version2: Union[Version, RawVersion],
) -> int:
    """
    Compares two dotted version strings numerically.

    Shorter versions are zero-padded, so ``1.2`` and ``1.2.0`` compare equal.

    Args:
        version1 (RawVersion): First dotted version string or a version integer tuple.
        version2 (RawVersion): Second dotted version string or a version integer tuple.

    Returns:
        int: ``-1`` if version1 precedes version2, ``1`` if it follows, ``0`` if they are equal.

    Raises:
        SystemError: If versions raw objects are not valid.
    """
    if not isinstance(version1, Version):
        version1 = _split_version(version1)

    if not isinstance(version2, Version):
        version2 = _split_version(version2)

    if version1 == version2:
        return 0

    difference = int(version1 >= version2)
    return 2 * difference - 1
