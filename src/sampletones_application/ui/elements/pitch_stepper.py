from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.pitch_stepper import PitchStepperLayout
from sampletones_application.tags.general import (
    SUF_BUTTON_DECREMENT,
    SUF_BUTTON_INCREMENT,
    SUF_HANDLER_REGISTRY,
    SUF_INPUT,
    SUF_LABEL,
    SUF_TABLE,
    SUF_TEXT,
    SUF_TOOLTIP,
    TAG_GLOBAL_THEME_PITCH_STEPPER,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.dpg import dpg_delete_item, dpg_set_value
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_core.utils.pitch_kind import PitchValueKind
from sampletones_shared.types.application import Color, Sender
from sampletones_shared.utils.callbacks import CallbackMixin


class GUIPitchStepper(CallbackMixin):
    """A self-contained input control for a NES pitch-like value (a channel pitch or a noise period).

    It pairs a read-only integer readout with a text field that accepts an integer or a FamiTracker note
    name, flanked by ``[-]``/``[+]`` buttons that step by one and repeat while held. The control owns the
    value it displays, clamps and renders it through its :class:`PitchValueKind`, and reports the value
    through the single ``on_value_changed`` hook once editing settles, so a burst of steps drives one
    update rather than one per step. ``set_value`` seeds the readout without reporting, so a panel can
    load a value and then listen for edits.
    """

    def __init__(
        self,
        tag: str,
        parent: str,
        *,
        kind: PitchValueKind,
        initial_value: int,
        label: str,
        tooltip: str,
        status_message: str,
        status_bar: GUIStatusBar,
        layout: PitchStepperLayout,
        value_color: Color,
        shortcut_manager: ShortcutManager,
    ) -> None:
        self.on_value_changed: Optional[Callable[[int], None]] = None
        self._status_bar = status_bar

        self._tag = tag
        self._parent = parent
        self._kind = kind
        self._layout = layout
        self._label = label
        self._tooltip = tooltip
        self._status_message = status_message
        self._value_color = value_color
        self._shortcut_manager = shortcut_manager

        self._value = kind.clamp(initial_value)
        self._hold_direction: Optional[int] = None
        self._hold_timer: Optional[float] = None
        self._emit_token = 0

        self._label_tag = f"{tag}{SUF_LABEL}"
        self._value_tag = f"{tag}{SUF_TEXT}"
        self._input_tag = f"{tag}{SUF_INPUT}"
        self._table_tag = f"{tag}{SUF_TABLE}"
        self._decrement_button_tag = f"{self._input_tag}{SUF_BUTTON_DECREMENT}"
        self._increment_button_tag = f"{self._input_tag}{SUF_BUTTON_INCREMENT}"
        self._tooltip_tag = f"{tag}{SUF_TOOLTIP}"
        self._mouse_handler_tag = f"{tag}{SUF_HANDLER_REGISTRY}"
        self._input_handler_tag = f"{self._input_tag}{SUF_HANDLER_REGISTRY}"

        self._build()

    @property
    def value(self) -> int:
        return self._value

    def set_value(self, value: int) -> None:
        """Seeds the displayed value, clamping it into range and rendering it without reporting a change."""
        self._value = self._kind.clamp(value)
        self._render()

    def _build(self) -> None:
        self._clear_existing_items()
        with dpg.table(
            tag=self._table_tag,
            parent=self._parent,
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            resizable=False,
            width=-1,
            height=0,
        ):
            dpg.add_table_column(
                width=self._layout.label_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=self._layout.label_width,
            )
            dpg.add_table_column(
                width=self._layout.value_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=self._layout.value_width,
            )
            dpg.add_table_column(width_stretch=True)
            dpg.add_table_column(
                width=self._layout.button_column_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=self._layout.button_column_width,
            )
            dpg.add_table_column(
                width=self._layout.button_column_width,
                width_fixed=True,
                no_resize=True,
                init_width_or_weight=self._layout.button_column_width,
            )
            with dpg.table_row():
                with dpg.table_cell():
                    dpg.add_text(self._label, tag=self._label_tag)
                with dpg.table_cell():
                    dpg.add_text(
                        str(self._value),
                        tag=self._value_tag,
                        color=self._value_color,
                    )
                    FontRegistry.bind_to_item(self._value_tag, Font.MONO)
                with dpg.table_cell():
                    dpg.add_input_text(
                        tag=self._input_tag,
                        default_value=self._kind.to_name(self._value),
                        width=-1,
                        on_enter=False,
                    )
                    FontRegistry.bind_to_item(self._input_tag, Font.MONO)
                with dpg.table_cell():
                    GUIButton(
                        label="-",
                        tag=self._decrement_button_tag,
                        width=self._layout.button_width,
                        callback=self._on_decrement,
                    )
                with dpg.table_cell():
                    GUIButton(
                        label="+",
                        tag=self._increment_button_tag,
                        width=self._layout.button_width,
                        callback=self._on_increment,
                    )

        ThemeRegistry.get(TAG_GLOBAL_THEME_PITCH_STEPPER).bind_to_item(self._table_tag)
        show_tooltip(self._input_tag, self._tooltip, tag=self._tooltip_tag)
        self._status_bar.bind_to_item(self._input_tag, self._status_message)
        self._setup_input_handler()
        self._setup_button_hold_handlers()

    def _clear_existing_items(self) -> None:
        """Removes the widget's own items from a prior build so the control rebuilds cleanly when a panel
        recreates it under the same tags. Deleting the table removes its rows, the readout, the input, and
        the buttons; the tooltip and the two handler registries live outside the table, so they are removed
        on their own."""
        for tag in (self._tooltip_tag, self._mouse_handler_tag, self._input_handler_tag, self._table_tag):
            if dpg.does_item_exist(tag):
                dpg_delete_item(tag)

    def _setup_input_handler(self) -> None:
        with dpg.item_handler_registry(tag=self._input_handler_tag):
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_input_committed)

        dpg.bind_item_handler_registry(self._input_tag, self._input_handler_tag)

    def _setup_button_hold_handlers(self) -> None:
        with dpg.handler_registry(tag=self._mouse_handler_tag):
            dpg.add_mouse_down_handler(button=dpg.mvMouseButton_Left, callback=self._on_mouse_down)
            dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=self._on_mouse_release)

    def _render(self) -> None:
        dpg_set_value(self._input_tag, self._kind.to_name(self._value))
        dpg_set_value(self._value_tag, str(self._value))

    def _commit(self, value: int) -> None:
        self._value = self._kind.clamp(value)
        self._render()
        self._schedule_emit()

    def _schedule_emit(self) -> None:
        """Renders update on every step for immediate feedback, while reporting the value only once the
        user settles. Each change supersedes the previous token, so a burst of steps — including a held
        button — collapses into a single ``on_value_changed`` once ``commit_delay`` frames pass with no
        further change, sparing consumers a reload per step. The settle posts at ``commit_priority`` (the
        schedule tier) so it orders alongside the debounced regeneration it triggers rather than below it."""
        self._emit_token += 1
        CallbackQueue.add(
            self._emit_settled_value,
            self._emit_token,
            priority=self._layout.commit_priority,
            delay=self._layout.commit_delay,
        )

    def _emit_settled_value(self, token: int) -> None:
        if token == self._emit_token:
            self.call(self.on_value_changed, self._value)

    def _step(self, direction: int) -> None:
        self._commit(self._value + direction)

    def _apply_text(self, text: str) -> None:
        self._commit(self._kind.from_text(text, self._value))

    def _on_decrement(self, *_arguments: Any) -> None:
        self._step(-1)

    def _on_increment(self, *_arguments: Any) -> None:
        self._step(1)

    def _on_input_committed(self, *_arguments: Any) -> None:
        self._apply_text(dpg.get_value(self._input_tag))

    def _on_mouse_down(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        if not dpg.does_item_exist(self._decrement_button_tag) or not dpg.does_item_exist(self._increment_button_tag):
            dpg_delete_item(sender)
            return

        is_decrement = dpg.is_item_hovered(self._decrement_button_tag)
        is_increment = dpg.is_item_hovered(self._increment_button_tag)
        direction = self._update_hold_timer(is_decrement, is_increment, dpg.get_delta_time())
        if direction is not None:
            self._step(direction)

    def _on_mouse_release(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self._hold_timer = None
        self._hold_direction = None

    def _update_hold_timer(self, is_decrement: bool, is_increment: bool, delta_time: float) -> Optional[int]:
        """Drives click-and-hold repetition: the first frame of a press arms the timer with a longer
        initial delay, and each later frame repeats once the delay elapses. Returns the step direction on
        the frames that should advance the value, otherwise None.
        """
        if not is_decrement and not is_increment:
            return None

        direction = -1 if is_decrement else 1
        if self._hold_direction != direction or self._hold_timer is None:
            self._hold_direction = direction
            self._hold_timer = 3 * self._layout.hold_delay
            return None

        self._hold_timer -= delta_time
        if self._hold_timer > 0:
            return None

        self._hold_timer = self._layout.hold_delay
        return direction
