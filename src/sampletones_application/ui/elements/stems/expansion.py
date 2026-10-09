from typing import AbstractSet, Set


class OpenFolders:
    """The folders a reader has opened, held by the key their row is drawn under.

    Whether a folder stands open is what the reader last did to it rather than anything the setup
    records, so the list keeps it for as long as it is on screen and the model stays clear of it.
    A folder gathered afresh arrives closed, which is what a reader meets when a folder of
    thousands joins the list.
    """

    def __init__(self) -> None:
        self._open: Set[str] = set()

    def __bool__(self) -> bool:
        return bool(self._open)

    @property
    def keys(self) -> Set[str]:
        """The folders standing open, which is what a draw builds a region for."""
        return set(self._open)

    def stands_open(self, key: str) -> bool:
        return key in self._open

    def toggle(self, key: str) -> bool:
        """Opens a closed folder and closes an open one, answering how it now stands."""
        if key in self._open:
            self._open.discard(key)
            return False

        self._open.add(key)
        return True

    def hold_to(self, keys: AbstractSet[str]) -> None:
        """Holds the memory to the folders the list still draws, a folder beyond them having left."""
        self._open &= set(keys)
