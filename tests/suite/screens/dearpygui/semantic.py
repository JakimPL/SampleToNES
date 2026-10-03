from inspect import Parameter, signature
from typing import Any, Callable, Final, Optional, Sequence

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.items.reading import ItemReading, read_item
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.reach import UnreachableError, covering_modal

CallbackRunner = Callable[..., object]
POSITIONAL: Final = (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)


def invoke(
    item: Item,
    run: CallbackRunner,
) -> None:
    """Runs ``item``'s callback as DearPyGui runs it for a press, through ``run``. Runs on the render thread.

    This is the gesture for a control DearPyGui reports a position alone for, such as a menu entry. The
    control must exist, stand shown, answer a press and sit outside any other tree's modal window.
    The callback receives as many of the sender, the value and the user data as it declares, which
    is what DearPyGui hands it.

    Raises:
        UnreachableError: Naming what keeps a user from the control.
    """
    refusal = _refusal(read_item(item))
    if refusal is not None:
        raise UnreachableError(f"{item!r} is out of reach: {refusal}")

    callback = dpg.get_item_callback(item)
    if callback is None:
        raise UnreachableError(f"{item!r} answers no press: it carries no callback")

    arguments = (item, dpg.get_value(item), dpg.get_item_user_data(item))
    run(callback, *_declared(callback, arguments))


def choose(
    item: Item,
    value: Any,
    run: CallbackRunner,
) -> None:
    """Sets ``item`` to ``value`` and runs its callback as a pick of that option does. Runs on the render thread.

    This is the gesture for a choice DearPyGui draws as one item, such as a radio button's options or a
    combo's entries. The choice must stand in reach the way :func:`invoke` asks.

    Raises:
        UnreachableError: Naming what keeps a user from the choice.
    """
    refusal = _refusal(read_item(item))
    if refusal is not None:
        raise UnreachableError(f"{item!r} is out of reach: {refusal}")

    callback = dpg.get_item_callback(item)
    if callback is None:
        raise UnreachableError(f"{item!r} answers no choice: it carries no callback")

    dpg.set_value(item, value)
    arguments = (item, value, dpg.get_item_user_data(item))
    run(callback, *_declared(callback, arguments))


def _refusal(reading: ItemReading) -> Optional[str]:
    if not reading.exists:
        return "it does not exist"
    if not reading.shown:
        return "it or a container around it is hidden"
    if not reading.enabled:
        return "it is disabled"

    covering = covering_modal(reading.item)
    if covering is not None:
        return f"the modal window '{covering}' holds the screen"

    return None


def _declared(callback: Callable[..., object], arguments: Sequence[Any]) -> Sequence[Any]:
    parameters = signature(callback).parameters.values()
    if any(parameter.kind is Parameter.VAR_POSITIONAL for parameter in parameters):
        return arguments

    return arguments[: sum(1 for parameter in parameters if parameter.kind in POSITIONAL)]
