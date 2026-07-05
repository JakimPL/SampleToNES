from __future__ import annotations

from typing import Any, List, Optional

from anytree import Node
from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.types.callback import Callback
from sampletones_shared.types.data import SerializedData


class Arguments(BaseModel):
    """
    Frozen data structure for tree traversal function/method arguments.

    Encapsulates all information needed to execute a callback during tree
    traversal, including the target node, instance reference (for methods),
    and additional positional/keyword arguments.

    Attributes:
        self: Instance reference for method calls, None for function calls.
        node: Current tree node being processed.
        args: Positional arguments to pass to the callback.
        kwargs: Keyword arguments to pass to the callback.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    self: Optional[Any] = Field(default=None)
    node: Node = Field(..., frozen=True)
    args: List[Any] = Field(default_factory=list, frozen=True)
    kwargs: SerializedData = Field(default_factory=dict, frozen=True)

    @property
    def method(self) -> bool:
        """
        Indicates whether the arguments represent a method call.
        """
        return self.self is not None

    @classmethod
    def create(
        cls,
        method: bool,
        args: List[Any],
        kwargs: SerializedData,
    ) -> Arguments:
        """
        Factory method to create an Arguments instance from raw arguments.

        Extracts instance reference and node from arguments list based on
        whether the callback is a method or function, then constructs an
        Arguments instance with remaining arguments.

        Args:
            method: Whether the arguments are for a method call (True) or function call (False).
            args: Raw positional arguments list. For methods: [self, node, ...]. For functions: [node, ...].
            kwargs: Keyword arguments dictionary to pass to callback.

        Returns:
            Arguments instance ready for callback execution.

        Raises:
            ValueError: If insufficient arguments provided (methods need at least 2, functions need at least 1).
            TypeError: If self is None for method arguments.
        """
        if method:
            if len(args) < 2:
                raise ValueError("Insufficient arguments for method call, expected at least 'self' and 'node'")

            self, node = args[:2]
            if self is None:
                raise TypeError("Self cannot be None for method arguments")

            return cls(
                self=self,
                node=node,
                args=list(args[2:]),
                kwargs=kwargs,
            )

        if len(args) < 1:
            raise ValueError("Insufficient arguments for function call, expected at least 'node'")

        node = args[0]
        return cls(
            node=node,
            args=list(args[1:]),
            kwargs=kwargs,
        )

    def execute(self, function: Callback) -> None:
        """
        Execute the callback with stored arguments.

        Calls the callback function/method with appropriate signature based on
        whether this represents a method call (includes self) or function call.

        Args:
            function: Callback to execute with stored arguments.
        """
        if self.method:
            function(self.self, self.node, *self.args, **self.kwargs)
        else:
            function(self.node, *self.args, **self.kwargs)
