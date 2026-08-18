from sampletones_application.categories.elements.settings import (
    KeybindingActionElements,
    KeybindingCategoryElements,
)
from sampletones_application.utils.gui.shortcuts.ids import (
    EDITABLE_SHORTCUT_CATEGORIES,
    ShortcutCategory,
    ShortcutId,
)


class TestKeybindingActionElements:
    """The editor lists every action it can rebind, so each one carries a name a reader sees."""

    def test_every_editable_action_carries_an_element(self) -> None:
        missing = [
            shortcut_id.name
            for shortcut_id in ShortcutId
            if shortcut_id.category in EDITABLE_SHORTCUT_CATEGORIES
            and shortcut_id.name not in KeybindingActionElements.__members__
        ]

        assert missing == []

    def test_every_element_names_an_editable_action(self) -> None:
        editable = {
            shortcut_id.name for shortcut_id in ShortcutId if shortcut_id.category in EDITABLE_SHORTCUT_CATEGORIES
        }
        stray = [element.name for element in KeybindingActionElements if element.name not in editable]

        assert stray == []

    def test_the_dialog_actions_leave_out_the_ones_a_modal_is_operated_by(self) -> None:
        """Tab, Enter and Escape are how a dialog is used at all, which keeps them off the list."""
        structural = [shortcut_id.name for shortcut_id in ShortcutId if shortcut_id.category is ShortcutCategory.DIALOG]

        assert all(name not in KeybindingActionElements.__members__ for name in structural)


class TestKeybindingCategoryElements:
    def test_every_editable_category_carries_an_element(self) -> None:
        missing = [
            category.name
            for category in EDITABLE_SHORTCUT_CATEGORIES
            if category.name not in KeybindingCategoryElements.__members__
        ]

        assert missing == []

    def test_every_element_names_an_editable_category(self) -> None:
        editable = {category.name for category in EDITABLE_SHORTCUT_CATEGORIES}
        stray = [element.name for element in KeybindingCategoryElements if element.name not in editable]

        assert stray == []
