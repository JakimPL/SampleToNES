class GUIPanel:
    def __init__(self, tag: str, parent_tag: str, width: int = -1, height: int = -1, init: bool = False) -> None:
        self.tag = tag
        self.parent_tag = parent_tag
        self.width = width
        self.height = height

        if init:
            self.create_panel()

    def create_panel(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def set_callbacks(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")
