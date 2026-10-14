from dataclasses import dataclass, field
from typing import Optional

from sampletones_shared.types.callback import VoidCallback

from .driver import OutputStreamProtocol


@dataclass(eq=False)
class OutputLease:
    """A source's claim on the output device, from the moment it asks to play until it hands the claim back.

    A source streaming from a thread of its own asks for the output when it is asked to play, which
    is before its stream opens, so a request ranked below it is declined for the whole span it plays.
    The stream it opens later is opened under the lease and stays with it, so handing the lease back
    closes the stream too. Two leases are two claims, which is why a lease compares by identity.

    Attributes:
        priority: The rank the claim was granted at; a request ranked strictly below it is declined.
        release: Winds the holder's writing down whenever the device needs the output, and returns once
            the lease is handed back.
        stream: The stream opened under the lease, or ``None`` until one opens.
    """

    priority: int
    release: VoidCallback
    stream: Optional[OutputStreamProtocol] = field(default=None)
