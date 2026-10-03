from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.plus_minus_buttons import (
    PlusMinusButtonsLayout,
)
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_DECREMENT,
    SUF_BUTTON_INCREMENT,
    SUF_HANDLER_REGISTRY,
    SUF_TABLE,
    TAG_GLOBAL_THEME_PLUS_MINUS_BUTTONS,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_delete_item
from sampletones_shared.constants.symbols import MINUS, PLUS
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

HOLD_INITIAL_DELAY_FACTOR = 3


class PlusMinusOrder(Enum):
    """Which sign leads the two-column pair: ``[-] [+]`` or ``[+] [-]``."""

    MINUS_FIRST = auto()
    PLUS_FIRST = auto()


@dataclass
class HeldPress:
    """A press that went down on one of the pair's buttons, and the time left before it repeats."""

    direction: int
    remaining: float


class GUIPlusMinusButtons(CallbackMixin):
    """A styled pair of ``[-]``/``[+]`` buttons laid out in two table columns.

    The pair reports presses through ``on_decrement`` / ``on_increment``: ``[-]`` always
    decrements and ``[+]`` always increments, while ``order`` chooses which column each
    sign occupies. With ``hold_repeat`` a held button repeats its press after an initial
    delay, matching the stepping feel of a numeric field; otherwise each button fires once
    per click. A hold belongs to the button the press went down on and repeats while the
    pointer stays on it, so a press carried in from elsewhere steps nothing. Either button
    can be enabled or disabled independently, so a control can gray out a step that would
    have no effect.
    """

    def __init__(
        self,
        tag: str,
        parent: Sender,
        *,
        layout: PlusMinusButtonsLayout,
        order: PlusMinusOrder,
        hold_repeat: bool,
        increment_enabled: bool = True,
        decrement_enabled: bool = True,
        font: Font = Font.MONO_SMALL,
    ) -> None:
        self.on_increment: Optional[VoidCallback] = None
        self.on_decrement: Optional[VoidCallback] = None

        self._tag = tag
        self._parent = parent
        self._layout = layout
        self._order = order
        self._hold_repeat = hold_repeat
        self._font = font

        self._held: Optional[HeldPress] = None

        self._table_tag = compose_tag(tag, SUF_TABLE)
        self._decrement_button_tag = compose_tag(tag, SUF_BUTTON_DECREMENT)
        self._increment_button_tag = compose_tag(tag, SUF_BUTTON_INCREMENT)
        self._mouse_handler_tag = compose_tag(tag, SUF_HANDLER_REGISTRY)
        self._decrement_handler_tag = compose_tag(self._decrement_button_tag, SUF_HANDLER_REGISTRY)
        self._increment_handler_tag = compose_tag(self._increment_button_tag, SUF_HANDLER_REGISTRY)

        self._decrement_button: Optional[GUIButton] = None
        self._increment_button: Optional[GUIButton] = None

        self._build(
            increment_enabled=increment_enabled,
            decrement_enabled=decrement_enabled,
        )

    def set_decrement_enabled(self, enabled: bool) -> None:
        if self._decrement_button is not None:
            self._decrement_button.set_enabled(enabled)

    def delete(self) -> None:
        """Removes the buttons and, when hold-repeat is armed, the shared mouse handler."""
        self._clear_existing_items()

    def _build(
        self,
        *,
        increment_enabled: bool,
        decrement_enabled: bool,
    ) -> None:
        self._clear_existing_items()
        increment_leads = self._order is PlusMinusOrder.PLUS_FIRST
        with dpg.table(
            tag=self._table_tag,
            parent=self._parent,
            header_row=False,
            policy=dpg.mvTable_SizingFixedFit,
            resizable=False,
            width=0,
            height=0,
        ):
            dpg.add_table_column(
                width_fixed=True,
                init_width_or_weight=self._layout.button_width,
            )
            dpg.add_table_column(
                width_fixed=True,
                init_width_or_weight=self._layout.button_width,
            )
            with dpg.table_row():
                with dpg.table_cell():
                    self._add_button(
                        increment=increment_leads,
                        increment_enabled=increment_enabled,
                        decrement_enabled=decrement_enabled,
                    )
                with dpg.table_cell():
                    self._add_button(
                        increment=not increment_leads,
                        increment_enabled=increment_enabled,
                        decrement_enabled=decrement_enabled,
                    )

        ThemeRegistry.get(TAG_GLOBAL_THEME_PLUS_MINUS_BUTTONS).bind_to_item(self._table_tag)
        if self._hold_repeat:
            self._setup_button_hold_handlers()

    def _add_button(
        self,
        *,
        increment: bool,
        increment_enabled: bool,
        decrement_enabled: bool,
    ) -> None:
        if increment:
            self._increment_button = GUIButton(
                label=PLUS,
                tag=self._increment_button_tag,
                width=self._layout.button_width,
                height=self._layout.button_height,
                callback=self._on_increment,
                enabled=increment_enabled,
                font=self._font,
            )
        else:
            self._decrement_button = GUIButton(
                label=MINUS,
                tag=self._decrement_button_tag,
                width=self._layout.button_width,
                height=self._layout.button_height,
                callback=self._on_decrement,
                enabled=decrement_enabled,
                font=self._font,
            )

    def _clear_existing_items(self) -> None:
        """Removes the widget's own items from a prior build so it rebuilds cleanly under the same
        tags. Deleting the table removes its buttons; the handler registries live outside the
        table, so each is removed on its own."""
        for tag in (
            self._mouse_handler_tag,
            self._decrement_handler_tag,
            self._increment_handler_tag,
            self._table_tag,
        ):
            if dpg.does_item_exist(tag):
                dpg_delete_item(tag)

    def _setup_button_hold_handlers(self) -> None:
        if self._decrement_button is not None:
            self._bind_press_handler(
                self._decrement_button.button_tag,
                self._decrement_handler_tag,
                self._on_decrement_pressed,
            )
        if self._increment_button is not None:
            self._bind_press_handler(
                self._increment_button.button_tag,
                self._increment_handler_tag,
                self._on_increment_pressed,
            )

        with dpg.handler_registry(tag=self._mouse_handler_tag):
            dpg.add_mouse_down_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._on_mouse_down,
            )
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._on_mouse_release,
            )

    @staticmethod
    def _bind_press_handler(
        button_tag: str,
        handler_tag: str,
        on_pressed: VoidCallback,
    ) -> None:
        """Hears a press going down on one button, which is where a hold begins.

        The handler goes on the button itself, since the group wrapping it reports no clicks.
        """
        with dpg.item_handler_registry(tag=handler_tag):
            dpg.add_item_clicked_handler(
                button=dpg.mvMouseButton_Left,
                callback=on_pressed,
            )

        dpg.bind_item_handler_registry(button_tag, handler_tag)

    def _step(self, direction: int) -> None:
        if direction > 0:
            self.call(self.on_increment)
        else:
            self.call(self.on_decrement)

    def _on_increment(self, *_arguments: Any) -> None:
        self._step(1)

    def _on_decrement(self, *_arguments: Any) -> None:
        self._step(-1)

    def _on_decrement_pressed(self) -> None:
        self._arm_hold(-1)

    def _on_increment_pressed(self) -> None:
        self._arm_hold(1)

    def _arm_hold(self, direction: int) -> None:
        """Starts a hold on the button a press went down on, with a longer delay before the first repeat."""
        self._held = HeldPress(
            direction=direction,
            remaining=HOLD_INITIAL_DELAY_FACTOR * self._layout.hold_delay,
        )

    def _on_mouse_down(
        self,
        sender: Sender,
        _app_data: Any,
        _user_data: Any,
    ) -> None:
        if not dpg.does_item_exist(self._decrement_button_tag) or not dpg.does_item_exist(self._increment_button_tag):
            dpg_delete_item(sender)
            return

        direction = self._advance_hold(self._held_button_hovered(), dpg.get_delta_time())
        if direction is not None:
            self._step(direction)

    def _held_button_hovered(self) -> bool:
        """Whether the pointer stands on the button the hold began on."""
        if self._held is None:
            return False

        button = self._increment_button if self._held.direction > 0 else self._decrement_button
        return button is not None and bool(button.is_item_hovered())

    def _on_mouse_release(
        self,
        _sender: Sender,
        _app_data: Any,
        _user_data: Any,
    ) -> None:
        self._held = None

    def _advance_hold(
        self,
        hovered: bool,
        delta_time: float,
    ) -> Optional[int]:
        """Counts a hold down by one frame, answering its direction on each frame that repeats it.

        The hold counts while the pointer stays on the button the press went down on, and each
        repeat starts the shorter delay to the next one.

        Args:
            hovered: Whether the pointer stands on the button the hold began on.
            delta_time: The seconds the frame took.

        Returns:
            Optional[int]: The step direction on a frame that repeats the press, otherwise ``None``.
        """
        if self._held is None or not hovered:
            return None

        self._held.remaining -= delta_time
        if self._held.remaining > 0:
            return None

        self._held.remaining = self._layout.hold_delay
        return self._held.direction
