from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme

DISPLAY_SETTINGS_COMBINATION = "Ctrl+D"
DUPLICATE_FRAME_COMBINATION = "Ctrl+Ins"


def _press(text: str) -> KeyEvent:
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


class TestDisplaySettingsKey:
    """Ctrl+D opens the display settings, which the order table gave to duplicate-frame before."""

    def test_the_display_settings_read_under_the_combination_they_answer(self, shipped: ShortcutScheme) -> None:
        assert shipped.shortcut(ShortcutId.DISPLAY_SETTINGS).display() == DISPLAY_SETTINGS_COMBINATION

    def test_the_order_table_leaves_the_display_settings_key_alone(self, shipped: ShortcutScheme) -> None:
        """The order table sees a press first, so it answering none is what lets the dialog open
        while the cursor sits in the table."""
        assert shipped.action(ShortcutCategory.ORDER, _press(DISPLAY_SETTINGS_COMBINATION)) is None


class TestDuplicateFrameKey:
    """Duplicate-frame reads as "insert a copy" beside the table's Insert and ``+``."""

    def test_duplicate_frame_reads_under_the_combination_it_answers(self, shipped: ShortcutScheme) -> None:
        assert shipped.shortcut(ShortcutId.ORDER_DUPLICATE_FRAME).display() == DUPLICATE_FRAME_COMBINATION

    def test_duplicate_frame_answers_its_press_in_the_order_table(self, shipped: ShortcutScheme) -> None:
        action = shipped.action(ShortcutCategory.ORDER, _press(DUPLICATE_FRAME_COMBINATION))

        assert action is ShortcutId.ORDER_DUPLICATE_FRAME

    def test_adding_a_frame_keeps_the_unmodified_insert(self, shipped: ShortcutScheme) -> None:
        assert shipped.action(ShortcutCategory.ORDER, _press("Ins")) is ShortcutId.ORDER_ADD_FRAME
