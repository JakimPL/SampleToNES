from __future__ import annotations

from collections import deque
from copy import deepcopy
from enum import StrEnum
from typing import Any, Callable, Deque, List, Union

from sampletones_shared.types.callback import Callback

from .arguments import Arguments


class TreeTraversal(StrEnum):
    """
    Possible tree traversal strategies.
    """

    DFS = "dfs"
    BFS = "bfs"


def execute(
    function: Callback,
    collection: Union[Deque[Arguments], List[Arguments]],
    arguments: Arguments,
    traversal: TreeTraversal,
) -> None:
    """
    Execute callback on current node and queue its children for traversal.

    Executes the callback with current node's arguments, then adds all child
    nodes to the traversal collection with copied arguments.

    Child order depends on traversal type:
    reversed for DFS (stack-based LIFO), natural order for BFS (queue-based FIFO).

    Args:
        function: Callback to execute on the current node.
        collection: Stack (DFS) or queue (BFS) holding pending nodes.
        arguments: Arguments for current node execution.
        traversal: Traversal strategy determining child iteration order.
    """
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
    """
    Decorator factory for tree traversal with specified strategy.

    Creates a decorator that wraps a callback function/method to execute it
    on every node in a tree using the specified traversal strategy (DFS or BFS).
    The decorated function receives a tree root node and traverses the entire
    subtree automatically.

    DFS (Depth-First Search): Uses a stack for LIFO processing. Visits nodes
    deeply before breadth, going down branches before visiting siblings.

    BFS (Breadth-First Search): Uses a queue for FIFO processing. Visits nodes
    level by level, processing all siblings before moving to children.

    Args:
        traversal: Traversal strategy to use (TreeTraversal.DFS or TreeTraversal.BFS).
        method: Whether decorated callback is a method (True) or function (False).
            Determines argument extraction: methods expect (self, node, ...), functions expect (node, ...).

    Returns:
        Decorator function that wraps callbacks with tree traversal logic.

    Raises:
        ValueError: If traversal is not TreeTraversal.DFS or TreeTraversal.BFS.
        ValueError: If insufficient arguments provided to decorated callback (see Arguments.create).
        TypeError: If self is None when method=True (see Arguments.create).

    Example:
        >>> from anytree import Node
        >>> @traverse(TreeTraversal.DFS, method=False)
        ... def print_node(node: Node) -> None:
        ...     print(node.name)
        ...
        >>> root = Node("root")
        >>> child1 = Node("child1", parent=root)
        >>> child2 = Node("child2", parent=root)
        >>> print_node(root)
        root
        child1
        child2
    """

    def decorator(function: Callback) -> Callback:
        def wrapper(*args: Any, **kwargs: Any) -> None:
            arguments = Arguments.create(method, list(args), kwargs)
            if traversal == TreeTraversal.DFS:
                stack = [arguments]

                while stack:
                    new_arguments = stack.pop()
                    execute(function, stack, new_arguments, traversal)

            elif traversal == TreeTraversal.BFS:
                queue = deque([arguments])

                while queue:
                    new_arguments = queue.popleft()
                    execute(function, queue, new_arguments, traversal)

            else:
                raise ValueError(f"Unsupported traversal type: {traversal}")

        return wrapper

    return decorator
