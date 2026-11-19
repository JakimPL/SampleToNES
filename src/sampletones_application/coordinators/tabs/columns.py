from typing import Callable, Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.parameters.geometry import TabGeometry
from sampletones_application.tags.general import TAG_GLOBAL_THEME_PANEL_SURFACE
from sampletones_application.ui.elements.layout.columns import ColumnSpec
from sampletones_shared.types.callback import StringCallback, VoidCallback

CollapseHandler = Callable[[str, bool], None]


def persisting_collapse(session_manager: SessionManager, then: Optional[VoidCallback]) -> CollapseHandler:
    """A card's collapse handler: it keeps the card's collapsed state for the next launch, then runs
    ``then`` where collapsing the card reflows what stands around it.

    Args:
        session_manager: The session the collapsed state is kept in.
        then: The reflow a collapse calls for, or ``None`` for a card whose column keeps its size.

    Returns:
        CollapseHandler: The handler a card's collapse toggle calls with its tag and state.
    """

    def handle(card_tag: str, collapsed: bool) -> None:
        session_manager.set_card_collapsed(card_tag, collapsed)
        if then is not None:
            then()

    return handle


def side_column(geometry: TabGeometry, *, tag: str, build: StringCallback) -> ColumnSpec:
    """The fixed side column a tab docks its full-height browser card in, a single raised surface.

    Args:
        geometry: The geometry every tab lays its columns out on.
        tag: The column's tag.
        build: What fills the column, handed the column's tag as its parent.

    Returns:
        ColumnSpec: The column, at the side width and height every tab shares.
    """
    return ColumnSpec(
        tag=tag,
        build=build,
        theme=TAG_GLOBAL_THEME_PANEL_SURFACE,
        width=geometry.side_width,
        height=geometry.side_height,
        no_scrollbar=True,
    )
