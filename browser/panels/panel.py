class GUIPanel:
    def __init__(self, tag: str, parent_tag: str, width: int = -1, height: int = -1) -> None:
        self.tag = tag
        self.parent_tag = parent_tag
        self.width = width
        self.height = height

    def create_panel(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")
