from typing import Any, Optional

from sampletones.types.callback import Callback

from .logger import logger


class CallbackMixin:
    """
    Mixin class providing callback management functionality.

    This mixin allows classes to safely handle optional callbacks.
    It supports dynamic callback registration and provides a safe invocation
    mechanism that handles missing callbacks.

    Classes inheriting this mixin can define callback attributes and use the
    provided methods to manage and invoke them. The mixin logs warnings
    when attempting to call None callbacks and validates callback types before
    invocation and assignment.
    """

    def call(self, callback: Optional[Callback], *args: Any, **kwargs: Any) -> Any:
        """
        Safely invokes a callback with provided arguments.

        Handles None callbacks gracefully by logging a warning and returning None.
        Validates that the callback is callable before invocation.

        Args:
            callback: The callback function to invoke, or None.
            *args: Positional arguments to pass to the callback.
            **kwargs: Keyword arguments to pass to the callback.

        Returns:
            The return value of the callback, or None if callback is None.

        Raises:
            TypeError: If callback is not None but is not callable.
        """
        if callback is None:
            logger.warning(f"No callback for {self.__class__.__name__} to call.")
            return None

        if not callable(callback):
            raise TypeError("Provided callback is not callable")

        return callback(*args, **kwargs)

    def set_callbacks(
        self,
        **callbacks: Optional[Callback],
    ) -> None:
        """
        Dynamically sets multiple callback attributes.

        Validates that each callback attribute exists on the instance before
        setting. Only sets callbacks that are both not None and callable.

        To reset a callback, use `reset_callbacks` method.

        Args:
            **callbacks: Keyword arguments where keys are attribute names and
                values are optional callback functions to set.

        Raises:
            AttributeError: If any callback name does not correspond to an
                existing attribute on the instance.
        """
        for name, callback in callbacks.items():
            if not hasattr(self, name):
                raise AttributeError(f"{self.__class__.__name__} has no attribute '{name}' to set callback")

            if callback is not None and callable(callback):
                setattr(self, name, callback)

    def reset_callbacks(self, *names: str) -> None:
        """
        Resets specified callback attributes to None.

        Validates that each callback attribute exists on the instance before
        resetting.

        Args:
            *names: Names of the callback attributes to reset.

        Raises:
            AttributeError: If any callback name does not correspond to an
                existing attribute on the instance.
        """
        for name in names:
            if not hasattr(self, name):
                raise AttributeError(f"{self.__class__.__name__} has no attribute '{name}' to reset callback")

            setattr(self, name, None)
