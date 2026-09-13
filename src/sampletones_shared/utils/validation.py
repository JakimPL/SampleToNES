from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Generic, List, Optional, Tuple, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

ModelTypeT = TypeVar("ModelTypeT", bound=BaseModel)
Location = Tuple[Union[str, int], ...]
VALUE_ERROR: Final[str] = "value_error"


@dataclass(frozen=True)
class RecoveredModel(Generic[ModelTypeT]):
    """
    Outcome of a recovering validation.

    Attributes:
        model: The validated model, carrying every stored value that satisfies the
            current schema and model defaults for everything else.
        dropped: The locations that were present in the input yet discarded because
            they failed validation. Locations that were absent and filled by defaults
            are excluded.
    """

    model: ModelTypeT
    dropped: Tuple[Location, ...]


def flatten_location(location: Location) -> str:
    """
    Renders a Pydantic error location as a dotted path for display.

    Mapping keys join with a dot and list indices append in brackets, so
    ``("generation", "drive")`` becomes ``generation.drive`` and
    ``("generators", 2)`` becomes ``generators[2]``.
    """
    parts: List[str] = []
    for item in location:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        elif parts:
            parts.append(f".{item}")
        else:
            parts.append(item)

    return "".join(parts)


def describe_failure(error: ValueError) -> str:
    """
    Renders a refused value the way a command line reports it, one line per problem.

    A reason a validator raised keeps its own words, and a broken constraint is named by the
    field it binds, so a person reads what to change and where.

    Args:
        error: The failure, a Pydantic validation error or a plain ``ValueError``.

    Returns:
        str: The reasons, one per line.
    """
    match error:
        case ValidationError():
            return "\n".join(_describe_detail(detail) for detail in error.errors())
        case _:
            return str(error)


def _describe_detail(detail: ErrorDetails) -> str:
    context = detail.get("ctx")
    if detail["type"] == VALUE_ERROR and context is not None:
        return str(context["error"])

    location = flatten_location(tuple(detail["loc"]))
    return f"{location}: {detail['msg']}" if location else detail["msg"]


def validate_with_recovery(
    model_class: Type[ModelTypeT],
    data: Mapping[str, Any],
) -> RecoveredModel[ModelTypeT]:
    """
    Validates ``data`` against ``model_class``, preserving the maximal valid subset.

    On a validation failure the offending location reported by Pydantic is removed
    from a copy of the input and validation is retried, so every value that still
    satisfies the schema survives while incompatible values fall back to model
    defaults. Removing one location per pass keeps list indices stable across
    cascading errors and guarantees termination, since each pass shrinks the input.

    A value, type, or ``extra_forbidden`` error removes the leaf it addresses. A
    ``missing`` error addresses an absent field, so recovery escalates to the
    nearest present ancestor whose sub-model then falls back to its default.

    Args:
        model_class: The Pydantic model to construct.
        data: The stored mapping to validate.

    Returns:
        The recovered model together with the locations that were discarded.

    Raises:
        ValidationError: When a required field without a default is absent and no
            present ancestor can be removed to restore a default.
    """
    return _RecoveringValidator(model_class, data).run()


class _RecoveringValidator(Generic[ModelTypeT]):
    """
    Carries the mutable state of one recovery pass over a stored mapping.

    Holding the working copy and the dropped locations as instance fields keeps the
    per-pass state in one place, so the recovery steps read and mutate it directly
    while ``validate_with_recovery`` remains the public entry point.
    """

    def __init__(self, model_class: Type[ModelTypeT], data: Mapping[str, Any]) -> None:
        self._model_class = model_class
        self._working: Any = copy.deepcopy(dict(data))
        self._dropped: List[Location] = []

    def run(self) -> RecoveredModel[ModelTypeT]:
        while True:
            try:
                model = self._model_class.model_validate(self._working)
            except ValidationError as error:
                location = self._select_removable_location(error)
                if location is None:
                    raise

                self._remove_location(location)
                self._dropped.append(location)
                continue

            return RecoveredModel(model=model, dropped=tuple(self._dropped))

    def _select_removable_location(self, error: ValidationError) -> Optional[Location]:
        for entry in error.errors():
            location: Location = tuple(entry["loc"])
            prefix = self._existing_prefix(self._working, location)
            if prefix:
                return prefix

        return None

    @staticmethod
    def _existing_prefix(container: Any, location: Location) -> Location:
        node: Any = container
        length = 0
        for index, key in enumerate(location):
            if isinstance(node, Mapping) and key in node:  # noqa: SIM114
                node = node[key]
            elif isinstance(node, list) and isinstance(key, int) and -len(node) <= key < len(node):
                node = node[key]
            else:
                break

            length = index + 1

        return location[:length]

    def _remove_location(self, location: Location) -> None:
        node: Any = self._working
        for key in location[:-1]:
            node = node[key]

        del node[location[-1]]
