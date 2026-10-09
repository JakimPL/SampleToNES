import copy
from collections.abc import Hashable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import PurePath
from typing import Any, Final, List, Literal, Set, Tuple, Union, get_origin

import numpy as np
from pydantic import BaseModel

from sampletones_core.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_core.structures import IdentifiedCollection

PROJECT_PARTS: Final[Tuple[str, ...]] = ("metadata", "info", "settings", "song", "voices")
SAMPLE_PARTS: Final[Tuple[str, ...]] = ("id", "name", "reconstruction")
TEXT_MARK: Final[str] = "~"
PATH_MARK: Final[str] = "elsewhere"
NUMBER_STEP: Final[float] = 0.5
TIME_STEP: Final[timedelta] = timedelta(seconds=1)


@dataclass(frozen=True)
class Attribute:
    name: str


@dataclass(frozen=True)
class Item:
    key: Hashable


PathStep = Union[Attribute, Item]


@dataclass(frozen=True)
class Leaf:
    """One field of the project, named by the model declaring it and reached by ``path``."""

    label: str
    path: Tuple[PathStep, ...]


def _child(
    node: Any,
    step: PathStep,
) -> Any:
    match step:
        case Attribute(name=name):
            return vars(node)[name]
        case Item(key=key):
            return node[key]


def _with_child(
    node: Any,
    step: PathStep,
    child: Any,
) -> Any:
    """``node`` holding ``child`` at ``step``: changed where it stands, or rebuilt where it is a tuple."""
    match step:
        case Attribute(name=name):
            object.__setattr__(node, name, child)
            return node
        case Item(key=key) if isinstance(node, tuple) and isinstance(key, int):
            return node[:key] + (child,) + node[key + 1 :]
        case Item(key=key):
            node[key] = child
            return node


def _replaced(
    node: Any,
    path: Tuple[PathStep, ...],
    leaf: Any,
) -> Any:
    if not path:
        return leaf

    step, rest = path[0], path[1:]
    child = _child(node, step)
    changed = _replaced(child, rest, leaf)
    return node if changed is child else _with_child(node, step, changed)


def _perturbed(value: Any) -> Any:
    """A value of the same kind that differs from ``value``."""
    match value:
        case bool():
            return not value
        case Enum():
            members = list(type(value))
            return members[(members.index(value) + 1) % len(members)]
        case int():
            return value + 1
        case float():
            return value + NUMBER_STEP
        case str():
            return value + TEXT_MARK
        case PurePath():
            return value / PATH_MARK
        case datetime():
            return value + TIME_STEP
        case np.ndarray():
            return value + 1

    raise TypeError(f"No perturbation for {type(value).__name__}")


def _is_leaf(value: Any) -> bool:
    return isinstance(value, (bool, Enum, int, float, str, PurePath, datetime, np.ndarray))


class _LeafWalk:
    """Collects one leaf per declaring model and field, the first instance the walk meets."""

    def __init__(self) -> None:
        self.leaves: List[Leaf] = []
        self._labels: Set[str] = set()

    def visit(
        self,
        node: Any,
        path: Tuple[PathStep, ...],
        label: str,
    ) -> None:
        match node:
            case None:
                return
            case _ if _is_leaf(node):
                self._take(label, path)
            case Sample():
                for name in SAMPLE_PARTS:
                    self.visit(vars(node)[name], path + (Attribute(name),), f"Sample.{name}")
            case IdentifiedCollection():
                for position, voice in enumerate(node):
                    self.visit(voice, path + (Item(position),), label)
            case BaseModel():
                for name, info in type(node).model_fields.items():
                    if get_origin(info.annotation) is not Literal:
                        self.visit(vars(node)[name], path + (Attribute(name),), f"{type(node).__name__}.{name}")
            case list() | tuple():
                for index, value in enumerate(node):
                    self.visit(value, path + (Item(index),), f"{label}[]")
            case dict():
                for key, value in node.items():
                    self.visit(value, path + (Item(key),), f"{label}{{}}")
            case _:
                raise TypeError(f"The walk meets a {type(node).__name__} at {label}")

    def _take(
        self,
        label: str,
        path: Tuple[PathStep, ...],
    ) -> None:
        if label not in self._labels:
            self._labels.add(label)
            self.leaves.append(Leaf(label=label, path=path))


def project_leaves(project: Project) -> List[Leaf]:
    """One leaf for every field any model in the project declares, wherever it first holds a value.

    The walk takes the fields holding a value. A literal tag names its model's kind with its one
    value, so the walk passes over it.
    """
    walk = _LeafWalk()
    for name in PROJECT_PARTS:
        walk.visit(vars(project)[name], (Attribute(name),), f"Project.{name}")

    return walk.leaves


def perturbed_project(
    project: Project,
    leaf: Leaf,
) -> Project:
    """An independent copy of ``project`` with the one field ``leaf`` names changed."""
    copied = copy.deepcopy(project)
    value = copied
    for step in leaf.path:
        value = _child(value, step)

    _replaced(copied, leaf.path, _perturbed(value))
    return copied
