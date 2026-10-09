from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from pathlib import PurePath
from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    Dict,
    Final,
    FrozenSet,
    List,
    Literal,
    Set,
    Tuple,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.project import Project
from sampletones_core.project.info import ProjectInfo
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.song import Song
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.structures import IdentifiedCollection

SHELLS: Final[FrozenSet[type]] = frozenset(
    {Project, ProjectInfo, ProjectSettings, IdentifiedCollection, Sample, Instrument, Song, Channel}
)
CONTAINER_SHELLS: Final[FrozenSet[type]] = frozenset({IdentifiedCollection})
LEAVES: Final[Tuple[type, ...]] = (bool, int, float, str, Enum, PurePath, datetime, NoneType)
READ_ONLY_CONTAINERS: Final[Tuple[Any, ...]] = (tuple, frozenset, Mapping)
CHANGEABLE_CONTAINERS: Final[Tuple[Any, ...]] = (list, dict, set)
REACHED: Final[FrozenSet[str]] = frozenset(
    {
        "Reconstruction",
        "InstructionsItem",
        "PulseInstruction",
        "StemsData",
        "ChannelAssignment",
        "StemSettings",
        "Config",
        "Pattern",
        "Row",
        "NoteOn",
        "Step",
        "InstrumentEnvelopes",
        "Metadata",
    }
)


class _ValueWalk:
    """Reads every class a project reaches and holds each to being a declared shell or a value.

    A value is frozen and holds values alone: scalars, read-only containers of values, and other
    values. A shell may hold anything, and whatever value it holds is held to the same rule. A
    container shell holds what its type argument names, which the walk reads from the argument.
    """

    def __init__(self) -> None:
        self.faults: List[str] = []
        self._visited: Set[type] = set()

    @property
    def visited(self) -> FrozenSet[type]:
        """Every class the walk has read."""
        return frozenset(self._visited)

    def visit_class(self, cls: type, path: str) -> None:
        if cls in self._visited:
            return

        self._visited.add(cls)
        holder_is_value = cls not in SHELLS
        if holder_is_value and not (issubclass(cls, BaseModel) and cls.model_config.get("frozen")):
            self.faults.append(f"{path}: {cls.__name__} is a value that can change")

        if cls in CONTAINER_SHELLS:
            return

        for name, annotation in self._fields(cls).items():
            self.visit(annotation, holder_is_value, f"{cls.__name__}.{name}")

    @staticmethod
    def _fields(cls: type) -> Dict[str, Any]:
        if issubclass(cls, BaseModel):
            return {name: info.annotation for name, info in cls.model_fields.items()}

        hints = get_type_hints(cls.__init__)
        hints.pop("return", None)
        return hints

    def visit(
        self,
        annotation: Any,
        holder_is_value: bool,
        path: str,
    ) -> None:
        origin = get_origin(annotation)
        arguments = [argument for argument in get_args(annotation) if argument is not Ellipsis]
        if origin is Annotated:
            self.visit(arguments[0], holder_is_value, path)
        elif origin in (Union, UnionType) or origin in READ_ONLY_CONTAINERS:
            for argument in arguments:
                self.visit(argument, holder_is_value, path)
        elif origin is Literal:
            return
        elif origin in CHANGEABLE_CONTAINERS:
            if holder_is_value:
                self.faults.append(f"{path}: a value holds a {origin.__name__}")
            for argument in arguments:
                self.visit(argument, holder_is_value, path)
        elif origin is not None:
            self.visit(origin, holder_is_value, path)
            for argument in arguments:
                self.visit(argument, holder_is_value, path)
        elif annotation is np.ndarray:
            if holder_is_value:
                self.faults.append(f"{path}: a value holds an array")
        elif isinstance(annotation, type) and issubclass(annotation, LEAVES):
            return
        elif isinstance(annotation, type):
            if holder_is_value and annotation in SHELLS:
                self.faults.append(f"{path}: a value holds the shell {annotation.__name__}")
            self.visit_class(annotation, path)
        else:
            self.faults.append(f"{path}: the walk cannot read {annotation!r}")


class _ChangeableValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    rows: List[int]


class _UnfrozenValue(BaseModel):
    count: int


class TestEveryValueIsImmutable:
    """Every class a project reaches is a declared shell or a value that never changes once made.

    A snapshot shares the values and copies the shells, so a value that could change in place would
    change every history entry holding it. The walk reads the types a project declares, and a
    changeable container or an unfrozen model anywhere under a value is reported.
    """

    def test_the_project_holds_shells_over_values(self) -> None:
        walk = _ValueWalk()

        walk.visit_class(Project, Project.__name__)

        assert walk.faults == []

    def test_a_list_inside_a_value_is_reported(self) -> None:
        walk = _ValueWalk()

        walk.visit_class(_ChangeableValue, _ChangeableValue.__name__)

        assert walk.faults == ["_ChangeableValue.rows: a value holds a list"]

    def test_an_unfrozen_model_is_reported(self) -> None:
        walk = _ValueWalk()

        walk.visit_class(_UnfrozenValue, _UnfrozenValue.__name__)

        assert walk.faults == ["_UnfrozenValue: _UnfrozenValue is a value that can change"]

    def test_the_walk_reaches_the_values_a_project_holds(self) -> None:
        walk = _ValueWalk()

        walk.visit_class(Project, Project.__name__)

        reached = {cls.__name__ for cls in walk.visited}
        assert REACHED <= reached
