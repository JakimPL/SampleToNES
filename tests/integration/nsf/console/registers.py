from typing import Dict, List

from sampletones_tools.player.trace.trace import RegisterTrace


def register_file(trace: RegisterTrace) -> List[Dict[int, int]]:
    """The APU as the driver leaves it after initialization and after every call that sounds.

    A tick reaches the hardware as the values standing in the registers once its writes land, and
    the three registers written only on change keep the value an earlier tick left there. Reading
    the whole file back after each sounding call is therefore what recovers a tick's full state
    from a trace that states only what changed.

    Args:
        trace: The writes a run of the driver made.

    Returns:
        List[Dict[int, int]]: One register file per tick the run sounded, in order.
    """
    registers: Dict[int, int] = {}
    ticks: List[Dict[int, int]] = []

    for writes in (trace.initialization, *trace.play_calls):
        if not writes:
            continue

        for write in writes:
            registers[write.address] = write.value

        ticks.append(dict(registers))

    return ticks
