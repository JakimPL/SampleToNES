from typing import Any, Optional

from sampletones_shared.types.callback import Callback

from ..logger import logger


class CallbackMixin:
    """Safe optional-callback invocation for logic and manager classes.

    Logic objects, managers, and controllers communicate with the layers above
    them exclusively through optional callback attributes (``on_x:
    Optional[Callback] = None``).  This mixin provides the machinery to invoke
    those hooks without callers having to guard for ``None`` everywhere, and to
    set or reset them in bulk.

    Responsibilities:
    - Invoke an optional callback safely (``call``), logging a warning when the
      hook is ``None`` rather than raising.
    - Validate and set multiple hooks at once (``set_callbacks``).
    - Reset hooks back to ``None`` by name (``reset_callbacks``).

    Governing principles:
    - A class that inherits this mixin must declare its callback attributes
      explicitly (``on_x: Optional[Callback] = None``) so that
      ``set_callbacks`` can validate their names.
    - Logic must never call DPG, import from ``ui/``, or import from
      ``coordinators/``.  Callbacks are the only outbound communication channel.

    Used by: ``ProjectController``, ``ReconstructionManager``,
    ``ConverterLogic``, ``ExplorerLogic``, ``GUIPanel``, and most other
    objects that emit events to the layer above them.
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
