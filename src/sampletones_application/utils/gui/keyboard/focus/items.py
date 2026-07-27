from typing import Dict, Final, FrozenSet

from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind

TEXT_ENTRY_ITEM_TYPES: Final[FrozenSet[str]] = frozenset(
    {
        "mvAppItemType::mvInputText",
        "mvAppItemType::mvInputInt",
        "mvAppItemType::mvInputFloat",
        "mvAppItemType::mvInputDouble",
        "mvAppItemType::mvSliderInt",
        "mvAppItemType::mvSliderFloat",
        "mvAppItemType::mvDragInt",
        "mvAppItemType::mvDragFloat",
    }
)

CHOICE_ITEM_TYPES: Final[FrozenSet[str]] = frozenset({"mvAppItemType::mvCombo"})

FIELD_KINDS: Final[Dict[str, FieldKind]] = {
    **{item_type: FieldKind.TEXT_ENTRY for item_type in TEXT_ENTRY_ITEM_TYPES},
    **{item_type: FieldKind.CHOICE for item_type in CHOICE_ITEM_TYPES},
}

FOCUS_REPORTING_ITEM_TYPES: Final[FrozenSet[str]] = frozenset(
    {
        "mvAppItemType::mvGroup",
        "mvAppItemType::mvChildWindow",
    }
)


def field_kind(item_type: str) -> FieldKind:
    """The kind of field ``item_type`` names, or ``NONE`` for a widget that keeps no keys of its own."""
    return FIELD_KINDS.get(item_type, FieldKind.NONE)


def reports_child_focus(item_type: str) -> bool:
    """Whether an item of ``item_type`` reports the focus of the widgets inside it.

    A group and a child window carry the state of what they lay out, so their own focus answers for
    their whole subtree. Every other container answers for itself alone — a tab reports the focus of
    its own header — and the widgets below it are reached one by one.
    """
    return item_type in FOCUS_REPORTING_ITEM_TYPES
