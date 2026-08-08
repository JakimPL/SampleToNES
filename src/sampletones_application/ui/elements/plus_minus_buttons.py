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


class GUIPlusMinusButtons(CallbackMixin):
    """A styled pair of ``[-]``/``[+]`` buttons laid out in two table columns.

    The pair reports presses through ``on_decrement`` / ``on_increment``: ``[-]`` always
    decrements and ``[+]`` always increments, while ``order`` chooses which column each
    sign occupies. With ``hold_repeat`` a held button repeats its press after an initial
    delay, matching the stepping feel of a numeric field; otherwise each button fires once
    per click. Either button can be enabled or disabled independently, so a control can
    grey out a step that would have no effect.
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

        self._hold_direction: Optional[int] = None
        self._hold_timer: Optional[float] = None

        self._table_tag = compose_tag(tag, SUF_TABLE)
        self._decrement_button_tag = compose_tag(tag, SUF_BUTTON_DECREMENT)
        self._increment_button_tag = compose_tag(tag, SUF_BUTTON_INCREMENT)
        self._mouse_handler_tag = compose_tag(tag, SUF_HANDLER_REGISTRY)

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

    def _build(self, *, increment_enabled: bool, decrement_enabled: bool) -> None:
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
        tags. Deleting the table removes its buttons; the mouse handler registry lives outside the
        table, so it is removed on its own."""
        for tag in (self._mouse_handler_tag, self._table_tag):
            if dpg.does_item_exist(tag):
                dpg_delete_item(tag)

    def _setup_button_hold_handlers(self) -> None:
        with dpg.handler_registry(tag=self._mouse_handler_tag):
            dpg.add_mouse_down_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._on_mouse_down,
            )
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._on_mouse_release,
            )

    def _step(self, direction: int) -> None:
        if direction > 0:
            self.call(self.on_increment)
        else:
            self.call(self.on_decrement)

    def _on_increment(self, *_arguments: Any) -> None:
        self._step(1)

    def _on_decrement(self, *_arguments: Any) -> None:
        self._step(-1)

    def _on_mouse_down(
        self,
        sender: Sender,
        _app_data: Any,
        _user_data: Any,
    ) -> None:
        if not dpg.does_item_exist(self._decrement_button_tag) or not dpg.does_item_exist(self._increment_button_tag):
            dpg_delete_item(sender)
            return

        is_decrement = self._decrement_button is not None and bool(self._decrement_button.is_item_hovered())
        is_increment = self._increment_button is not None and bool(self._increment_button.is_item_hovered())
        direction = self._update_hold_timer(
            is_decrement,
            is_increment,
            dpg.get_delta_time(),
        )
        if direction is not None:
            self._step(direction)

    def _on_mouse_release(
        self,
        _sender: Sender,
        _app_data: Any,
        _user_data: Any,
    ) -> None:
        self._hold_timer = None
        self._hold_direction = None

    def _update_hold_timer(
        self,
        is_decrement: bool,
        is_increment: bool,
        delta_time: float,
    ) -> Optional[int]:
        """Drives click-and-hold repetition: the first frame of a press arms the timer with a longer
        initial delay, and each later frame repeats once the delay elapses. Returns the step direction on
        the frames that should advance the value, otherwise None.
        """
        if not is_decrement and not is_increment:
            return None

        direction = -1 if is_decrement else 1
        if self._hold_direction != direction or self._hold_timer is None:
            self._hold_direction = direction
            self._hold_timer = HOLD_INITIAL_DELAY_FACTOR * self._layout.hold_delay
            return None

        self._hold_timer -= delta_time
        if self._hold_timer > 0:
            return None

        self._hold_timer = self._layout.hold_delay
        return direction
