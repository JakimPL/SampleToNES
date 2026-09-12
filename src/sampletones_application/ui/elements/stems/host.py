from typing import Protocol


class StemsListHost(Protocol):
    """Which gestures a stems list reaches an owner with, as the list itself answers them.

    Picking a row out, sounding it and putting its menu up each reach past the row to whoever owns
    the list, and each is offered while an owner answers it. The list holds those hooks and an
    owner sets them when it likes, so the answer is read at the moment a gesture lands.
    """

    @property
    def activatable(self) -> bool: ...

    @property
    def playable(self) -> bool: ...

    @property
    def has_menu(self) -> bool: ...
