from functools import partial
from typing import Callable, Sequence

from sampletones_shared.types.callback import VoidCallback

Gate = Callable[[VoidCallback], None]


def pass_gates(gates: Sequence[Gate], arrive: VoidCallback) -> None:
    """Runs each gate in turn, and calls ``arrive`` once the last one lets the request through.

    Each gate receives a callback that runs the gates after it. A gate checks what it guards when
    it is reached: it calls the callback at once, or asks a question whose answer calls it. An
    earlier question is therefore answered before a later gate checks, and a state that cleared
    meanwhile asks nothing. A declined question stops the request there.

    Args:
        gates: What stands between a request and ``arrive``, in the order the gates are asked.
        arrive: What runs once every gate has let the request through.
    """
    if not gates:
        arrive()
        return

    gates[0](partial(pass_gates, gates[1:], arrive))
