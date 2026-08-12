from typing import Protocol


class EditSurfaceProtocol(Protocol):
    def owns_edit_actions(self) -> bool: ...

    def build_edit_actions(self) -> None: ...
