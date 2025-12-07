from ..utils.dpg import dpg_configure_item


class GUIPanel:
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = 0,
        height: int = 0,
        init: bool = False,
    ) -> None:
        self.tag = tag
        self.parent = parent
        self.width = width
        self.height = height

        if init:
            self.create_panel()

    def create_panel(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def set_callbacks(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def set_visibility(self, visible: bool) -> None:
        dpg_configure_item(self.tag, show=visible)

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)
