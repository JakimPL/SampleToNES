from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Deque, Dict, List, Optional, Union

from anytree import Node
from pydantic import BaseModel, ConfigDict, Field

from sampletones.typehints import Callback


class TreeTraversal(StrEnum):
    DFS = "dfs"
    BFS = "bfs"


@dataclass(frozen=True)
class Argument:
    value: Any


class Arguments(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    self: Optional[Any] = Field(default=None)
    node: Node = Field(..., frozen=True)
    args: List[Any] = Field(default_factory=list, frozen=True)
    kwargs: Dict[str, Any] = Field(default_factory=dict, frozen=True)
    method: bool = Field(default=True)

    @classmethod
    def get(
        cls,
        method: bool,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> Arguments:
        if method:
            self, node = args[:2]
            args = list(args[2:])
            return cls(self=self, node=node, args=args, kwargs=kwargs, method=method)

        node = args[0]
        args = list(args[1:])
        return cls(node=node, args=args, kwargs=kwargs, method=method)

    def execute(self, function: Callback) -> None:
        if self.method:
            function(self.self, self.node, *self.args, **self.kwargs)
        else:
            function(self.node, *self.args, **self.kwargs)


def execute(
    function: Callback,
    collection: Union[Deque[Arguments], List[Arguments]],
    arguments: Arguments,
    traversal: TreeTraversal,
) -> None:
    arguments.execute(function)
    children = reversed(arguments.node.children) if traversal == TreeTraversal.DFS else arguments.node.children
    for child in children:
        child_arguments = arguments.model_copy(
            update={
                "node": child,
                "args": deepcopy(arguments.args),
                "kwargs": deepcopy(arguments.kwargs),
            }
        )
        collection.append(child_arguments)


def traverse(traversal: TreeTraversal, method: bool = True) -> Callable[[Callback], Callback]:
    def decorator(function: Callback) -> Callback:
        def wrapper(*args: Any, **kwargs: Any) -> None:
            arguments = Arguments.get(method, list(args), kwargs)
            if traversal == TreeTraversal.DFS:
                stack = [arguments]

                while stack:
                    arguments = stack.pop()
                    execute(function, stack, arguments, traversal)

            elif traversal == TreeTraversal.BFS:
                queue = deque([arguments])

                while queue:
                    arguments = queue.popleft()
                    execute(function, queue, arguments, traversal)

            else:
                raise ValueError(traversal)

        return wrapper

    return decorator
