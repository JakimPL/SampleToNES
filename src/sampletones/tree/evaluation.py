from collections import deque
from enum import StrEnum
from typing import Any, Callable

from anytree import Node

from sampletones.typehints import Callback


class TreeEvaluation(StrEnum):
    DFS = "dfs"
    BFS = "bfs"


def tree(method: TreeEvaluation) -> Callable[[Callback], Callback]:
    def decorator(function: Callback) -> Callback:
        def wrapper(root: Node, *args: Any, **kwargs: Any) -> None:
            if method == TreeEvaluation.DFS:
                stack = [(root, args, kwargs)]

                while stack:
                    node, args, kwargs = stack.pop()
                    function(node, *args, **kwargs)
                    for child in reversed(node.children):
                        stack.append((child, args, kwargs))

            elif method == TreeEvaluation.BFS:
                queue = deque([(root, args, kwargs)])

                while queue:
                    node, args, kwargs = queue.popleft()
                    function(node, *args, **kwargs)
                    for child in node.children:
                        queue.append((child, args, kwargs))

            else:
                raise ValueError(method)

        return wrapper

    return decorator
