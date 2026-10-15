import os
from typing import Final, Optional, Protocol, Sequence, Tuple, cast

HIDE_SUPPORT_PROMPT: Final[str] = "PYGAME_HIDE_SUPPORT_PROMPT"
HIDDEN: Final[str] = "1"
DISTRIBUTION_NAME: Final[str] = "pygame-ce"
LIBRARY_NAME: Final[str] = "PortMidi"

DeviceInfo = Tuple[bytes, bytes, int, int, int]
PackedEvent = Tuple[Sequence[int], int]


class PortMidiInput(Protocol):
    """An open PortMidi input, as ``pygame.pypm`` names its methods."""

    # pylint: disable=invalid-name

    def Poll(self) -> int:
        """Whether events wait to be read."""

    def Read(self, max_events: int, /) -> Sequence[PackedEvent]:
        """Up to ``max_events`` events, each its four packed bytes and its timestamp."""

    def Close(self) -> None: ...


class PortMidiLibrary(Protocol):
    """What the backend calls of PortMidi, as ``pygame.pypm`` offers it.

    It keeps the library to one module, so the backend's thread and lifecycle are tested with a PortMidi of the
    case's own on every platform. PortMidi raises a bare ``Exception`` on every failure.
    """

    # pylint: disable=invalid-name

    def Initialize(self) -> None: ...

    def Terminate(self) -> None: ...

    def CountDevices(self) -> int: ...

    def GetDeviceInfo(self, device_id: int, /) -> Optional[DeviceInfo]:
        """The device's interface, name, whether it is an input, whether an output, and whether it is open."""

    def Input(self, device_id: int, buffer_size: int, /) -> PortMidiInput: ...


def load_portmidi() -> PortMidiLibrary:
    """PortMidi as pygame-ce carries it, imported without pygame's greeting on the standard output.

    Importing ``pygame.pypm`` runs the whole of pygame's package initialization, which prints a greeting unless
    the environment says otherwise, so the setting is made just before the import.

    Raises:
        ImportError: If pygame-ce is missing.
        OSError: If its PortMidi library fails to load.
    """
    os.environ.setdefault(HIDE_SUPPORT_PROMPT, HIDDEN)
    import pygame.pypm

    return cast(PortMidiLibrary, pygame.pypm)
