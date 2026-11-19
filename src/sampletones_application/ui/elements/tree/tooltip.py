from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_DETAIL_TOOLTIP,
    SUF_TOOLTIP_DETAIL,
    TAG_GLOBAL_THEME_TREE_WINDOW,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_get_item_user_data,
    dpg_is_item_hovered,
)
from sampletones_application.utils.gui.tooltip import (
    DetailSwatch,
    create_detail_tooltip,
    populate_detail_tooltip,
)
from sampletones_core.structures.tree import TreeNode
from sampletones_shared.types.application import Sender


@dataclass(frozen=True)
class NodeDetail:
    """What a row's tooltip lists: its settings, and the recordings its document is made of."""

    items: List[Tuple[str, str]]
    recordings: Tuple[DetailSwatch, ...]


class DetailTooltip:
    """The one tooltip a tree lists the details of the row under the pointer in.

    The tooltip is built once per tree and refilled for each row the pointer rests on, so a row's
    details are read once per visit.
    """

    def __init__(
        self,
        panel_tag: str,
        describe: Callable[[TreeNode], NodeDetail],
        *,
        swatch_label: str,
    ) -> None:
        self._describe = describe
        self._swatch_label = swatch_label
        self._swatch_glyph = ""
        self.tag = compose_tag(panel_tag, SUF_TOOLTIP_DETAIL)
        self._handler_tag = compose_tag(panel_tag, SUF_HANDLER_DETAIL_TOOLTIP)
        self.owner_tag: Optional[str] = None

    def create(self, tree_window_tag: str, *, swatch_glyph: str) -> None:
        """Builds the tooltip and the mouse handler that dismisses it.

        Binding the tooltip to the tree window keeps it visible while the pointer stays over the tree,
        and the handler clears it once the owning node's row is left, so the details track the hovered
        main node and disappear over the tree's blank space.
        """
        self._swatch_glyph = swatch_glyph
        ThemeRegistry.get(TAG_GLOBAL_THEME_TREE_WINDOW).bind_to_item(tree_window_tag)
        create_detail_tooltip(tree_window_tag, tag=self.tag)
        with dpg.handler_registry(tag=self._handler_tag):
            dpg.add_mouse_move_handler(callback=self._on_mouse_move)

    def follow(self, user_data: Any) -> None:
        """Reveals the tooltip for a hovered node that carries details, hiding it otherwise.

        A hover is reported for every frame the pointer rests on a row, and the row it belongs to is
        read first, so the content is built once per node and a row asked about a document asks for
        it once.
        """
        if not isinstance(user_data, tuple):
            return

        node, node_tag = user_data
        if self.owner_tag == node_tag:
            return

        self._show(node, node_tag)

    def refresh(self) -> None:
        """Rebuilds the tooltip where it stands, which an answer arriving after it was built asks for.

        The rebuild belongs to the row the tooltip is showing, so it stands still once the pointer
        has moved on.
        """
        owner_tag = self.owner_tag
        if owner_tag is None:
            return

        node = _node_at(owner_tag)
        if node is not None:
            self._show(node, owner_tag)

    def _show(self, node: TreeNode, node_tag: str) -> None:
        """Fills the tooltip with what the node answers, and hides it where the node answers nothing."""
        detail = self._describe(node)
        if not detail.items and not detail.recordings:
            self._hide()
            return

        populate_detail_tooltip(
            self.tag,
            detail.items,
            swatch_glyph=self._swatch_glyph,
            swatch_label=self._swatch_label,
            swatches=detail.recordings,
        )
        self.owner_tag = node_tag
        dpg_configure_item(self.tag, show=True)

    def _hide(self) -> None:
        if self.owner_tag is None:
            return

        self.owner_tag = None
        dpg_configure_item(self.tag, show=False)

    def _on_mouse_move(self, _sender: Sender, _app_data: Any) -> None:
        owner_tag = self.owner_tag
        if owner_tag is None:
            return

        if not dpg.does_item_exist(owner_tag) or not dpg_is_item_hovered(owner_tag):
            self._hide()


def _node_at(node_tag: str) -> Optional[TreeNode]:
    """The node a row was created for, read back from the widget the row is."""
    user_data = dpg_get_item_user_data(node_tag)
    if not isinstance(user_data, tuple):
        return None

    node, _ = user_data
    return node if isinstance(node, TreeNode) else None
