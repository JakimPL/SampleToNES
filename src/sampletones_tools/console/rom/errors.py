from sampletones_shared.exceptions.validation import InvalidDataError
from sampletones_tools.console.errors import ConsoleError


class NotAROMError(InvalidDataError):
    """The data a console was handed is no cartridge image: its header lacks the iNES signature."""


class UnsupportedCartridgeError(InvalidDataError):
    """The image names a board other than the one the console models."""


class ReadOnlyMemoryError(ConsoleError):
    """The program stored a byte into memory the cartridge holds as ROM."""


class BootOverrunError(ConsoleError):
    """The program spent its step budget, or came to rest, before it switched its frame interrupt on."""


class ConsoleStateError(ConsoleError):
    """The console was asked for a step its state has no place for, such as a frame ahead of the boot."""
