from enum import Enum
from typing import Final, Tuple


class Event(Enum):
    """Everything that reaches the session core: the render thread's requests and the writer's turns.

    The writer asks for its next step and then reports how the device call went, so a request from the render
    thread can fall between the two, as it does while the writer waits inside the device.
    """

    CLAIM_PREVIEW = "claim_preview"
    CLAIM_NORMAL = "claim_normal"
    STOP = "stop"
    STOP_ALL = "stop_all"
    PAUSE = "pause"
    RESUME = "resume"
    COMMAND = "command"
    RECONFIGURE = "reconfigure"
    CLOSE = "close"
    ABANDON = "abandon"
    DECIDE = "decide"
    SUCCEEDS = "succeeds"
    RUNS_OUT = "runs_out"
    SOURCE_FAILS = "source_fails"
    FAILS_ASIDE = "fails_aside"
    DEVICE_FAILS = "device_fails"


PREVIEW_RANK: Final[int] = 0
NORMAL_RANK: Final[int] = 1
DEVICE_ERROR: Final[OSError] = OSError("The device failed")
SOURCE_ERROR: Final[RuntimeError] = RuntimeError("The source failed")
FAILURES: Final[Tuple[Exception, ...]] = (DEVICE_ERROR, SOURCE_ERROR)
