from typing import List

from sampletones_application.utils.gui.keyboard.focus.items import (
    field_kind,
    reports_child_focus,
)
from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.focus.tree import (
    ItemNode,
    is_item_active,
    is_item_focused,
    read_item,
)
from sampletones_shared.types.application import Sender


def edited_field_kind(item: Sender) -> FieldKind:
    """The kind of field ``item`` is being edited as, whether directly or through its layout.

    A ``dpg.group`` reports the state of the widget inside it and DearPyGui names the outermost such
    group as the focused item, so a field laid out beside another widget — the instrument sequence
    input beside its copy button — reaches the keyboard as its group. An active group therefore
    answers with the field being edited below it, and a field answers for itself.
    """
    if not is_item_active(item):
        return FieldKind.NONE

    node = read_item(item)
    kind = field_kind(node.item_type)
    if kind is not FieldKind.NONE:
        return kind

    return _active_descendant_field_kind(node)


def _active_descendant_field_kind(node: ItemNode) -> FieldKind:
    """The kind of the active field below ``node``, or ``NONE`` when its subtree holds none.

    DearPyGui keeps one item active at a time, so the first active field the subtree yields is the
    one the user is editing.
    """
    pending: List[Sender] = list(node.children)
    while pending:
        child = read_item(pending.pop())
        kind = field_kind(child.item_type)
        if kind is not FieldKind.NONE:
            if is_item_active(child.item):
                return kind
        elif _leads_to_focused_widget(child):
            pending.extend(child.children)

    return FieldKind.NONE


def _leads_to_focused_widget(node: ItemNode) -> bool:
    """Whether the search follows ``node`` towards the field being edited.

    Through a container that carries its children's state the search follows the one branch that
    reports focus, which keeps a key press to the cost of the path down to its field. Every other
    container is entered on the way to the widgets below it.
    """
    if not reports_child_focus(node.item_type):
        return True

    return is_item_focused(node.item)
