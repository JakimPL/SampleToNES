from inspect import Parameter, signature
from typing import Any, Final, Sequence

import dearpygui.dearpygui as dpg

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import Callback

POSITIONAL: Final = (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)


def hold_callbacks() -> None:
    """Have DearPyGui gather a widget's callback rather than running it where the gesture lands.

    DearPyGui answers a gesture on a thread of its own, so a callback that rebuilds widgets there
    runs while the render loop is walking the very items it drops — a crash rather than a glitch.
    Gathered callbacks wait in a queue the frame drains, which is what makes every gesture reach
    the interface from the thread the context belongs to.
    """
    dpg.configure_app(manual_callback_management=True)


def run_held_callbacks() -> None:
    """Run what DearPyGui gathered since the last frame, on the thread that drew it.

    A callback is handed as many of DearPyGui's three arguments as it declares, and each runs
    through the reporting queued work runs through, so one failing gesture leaves the rest to run.
    """
    for job in dpg.get_callback_queue() or ():
        callback, *arguments = job
        if callback is None:
            continue

        CallbackQueue.run(callback, *_taken(callback, arguments))


def _taken(callback: Callback, arguments: Sequence[Any]) -> Sequence[Any]:
    """The arguments ``callback`` declares, out of the sender, the payload and the user data."""
    parameters = signature(callback).parameters.values()
    if any(parameter.kind is Parameter.VAR_POSITIONAL for parameter in parameters):
        return arguments

    return arguments[: sum(1 for parameter in parameters if parameter.kind in POSITIONAL)]
