from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.focus.search import edited_field_kind
from sampletones_application.utils.gui.keyboard.focus.tree import focused_item, item_exists


def focused_field_kind() -> FieldKind:
    """The kind of field editing the keyboard right now, or ``NONE`` when none is.

    The focused item is read straight from DearPyGui on each key press and counts only while it is
    actively being edited, so every input the user types into keeps its keys on its own. A combo
    counts only while its popup is open, when it owns the arrows and Escape, and a field the
    sequencer has since rebuilt away counts as no field focused.
    """
    item = focused_item()
    if item is None:
        return FieldKind.NONE

    if not item_exists(item):
        return FieldKind.NONE

    return edited_field_kind(item)


def is_field_focused() -> bool:
    """Whether any field is editing the keyboard, so plain keys stay with it.

    The scopes consult this single flag, so a key press stays with the field the user is typing
    into and reaches the panels and shortcuts otherwise.
    """
    return focused_field_kind() is not FieldKind.NONE
