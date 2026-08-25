from pathlib import Path
from typing import Dict, Final

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_shared.constants.general import HEXADECIMAL_BASE
from sampletones_shared.exceptions import DriverBuildError

LABEL_MARKER: Final[str] = "al"
LABEL_FIELDS: Final[int] = 3
SYMBOL_PREFIX: Final[str] = "."

LOAD_SYMBOL: Final[str] = "__PRG_START__"
INIT_SYMBOL: Final[str] = "nsf_init"
PLAY_SYMBOL: Final[str] = "nsf_play"
SONG_SYMBOL: Final[str] = "song_data"


def read_labels(path: Path) -> Dict[str, int]:
    """Reads the addresses a linker reported for its symbols.

    The label file lists one symbol per line as ``al <address> .<symbol>``, the format debuggers
    read a build's symbols through. Lines of that shape carry the addresses; the rest of the file
    describes the build itself.

    Args:
        path: The label file the linker wrote.

    Returns:
        Dict[str, int]: Each symbol's address, keyed by the symbol's own name.
    """
    labels: Dict[str, int] = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == LABEL_FIELDS and fields[0] == LABEL_MARKER:
            labels[fields[2].removeprefix(SYMBOL_PREFIX)] = int(
                fields[1],
                HEXADECIMAL_BASE,
            )

    return labels


def read_addresses(path: Path) -> DriverAddresses:
    """Reads where a linker laid the driver and the song behind it.

    A build states its own layout this way, so what the exporter reads about the image comes from
    the program that produced it.

    Args:
        path: The label file the linker wrote.

    Returns:
        DriverAddresses: The addresses the linker reported.

    Raises:
        DriverBuildError: If the linker reported no address for one of the four symbols.
    """
    labels = read_labels(path)
    return DriverAddresses(
        load=address_of(labels, LOAD_SYMBOL),
        init=address_of(labels, INIT_SYMBOL),
        play=address_of(labels, PLAY_SYMBOL),
        song=address_of(labels, SONG_SYMBOL),
    )


def address_of(labels: Dict[str, int], symbol: str) -> int:
    """The address a linker reported for one symbol.

    Args:
        labels: Each symbol's address, as :func:`read_labels` answers.
        symbol: The symbol to look up.

    Returns:
        int: Where the symbol lies.

    Raises:
        DriverBuildError: If the linker reported no address for the symbol.
    """
    if symbol not in labels:
        raise DriverBuildError(f"the linker reported no address for {symbol}")

    return labels[symbol]
