from dataclasses import dataclass


@dataclass(frozen=True)
class FileBrowserTags:
    """The DearPyGui tags naming one file browser's widgets, stated together where the browser is declared.

    Every browser builds the same arrangement — a panel card holding a controls group with a refresh
    button, and a window holding the group the tree attaches to — so the tags naming those widgets
    travel as one value the panel is constructed with. Stating them together makes each browser
    declare a complete set at one place, checked where it is written.
    """

    panel: str
    tree: str
    window_tree: str
    group_tree: str
    group_controls: str
    button_refresh: str
