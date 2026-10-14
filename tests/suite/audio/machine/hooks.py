from dataclasses import dataclass
from typing import Optional

from .calls import OpenCall, OpenHook, StreamCall, StreamHook


@dataclass
class MachineHooks:
    """What a case runs at the start of each call the fake device takes, on the thread making the call.

    A hook may raise to fail the call, wait to hold it, or act to place a race at that exact point.
    """

    before_open: Optional[OpenHook] = None
    before_write: Optional[StreamHook] = None
    before_drain: Optional[StreamHook] = None
    before_close: Optional[StreamHook] = None

    def opening(self, call: OpenCall) -> None:
        if self.before_open is not None:
            self.before_open(call)

    def writing(self, call: StreamCall) -> None:
        if self.before_write is not None:
            self.before_write(call)

    def draining(self, call: StreamCall) -> None:
        if self.before_drain is not None:
            self.before_drain(call)

    def closing(self, call: StreamCall) -> None:
        if self.before_close is not None:
            self.before_close(call)
