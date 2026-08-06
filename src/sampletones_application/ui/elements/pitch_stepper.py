from dataclasses import dataclass
from typing import Any, Callable, Optional, Self

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.general.pitch_stepper import PitchStepperLayout
from sampletones_application.layout.general.plus_minus_buttons import PlusMinusButtonsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTONS,
    SUF_HANDLER_REGISTRY,
    SUF_INPUT,
    SUF_LABEL,
    SUF_TABLE,
    SUF_TEXT,
    SUF_TOOLTIP,
    TAG_GLOBAL_THEME_PLUS_MINUS_BUTTONS,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.plus_minus_buttons import GUIPlusMinusButtons, PlusMinusOrder
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.dpg import dpg_delete_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.palette.color import PaletteColor
from sampletones_core.utils.pitch_kind import PitchValueKind
from sampletones_shared.types.application import Color
from sampletones_shared.utils.callbacks import CallbackMixin


@dataclass(frozen=True)
class PitchStepperStyle:
    """The styling a pitch stepper draws itself with, narrowed from the general layout.

    A stepper needs only its own dimensions, the plus/minus button dimensions it embeds, and
    the colour of its read-only value readout. Assembling this at the composition root lets a
    panel that builds steppers receive just these three fields, mirroring the
    :meth:`TreeColors.create` narrowing.
    """

    dimensions: PitchStepperLayout
    plus_minus: PlusMinusButtonsLayout
    value_color: PaletteColor

    @classmethod
    def from_general(cls, general: GeneralLayout) -> Self:
        return cls(
            dimensions=general.pitch_stepper,
            plus_minus=general.plus_minus_buttons,
            value_color=general.colors.text.disabled,
        )


class GUIPitchStepper(CallbackMixin):
    """A self-contained input control for a NES pitch-like value (a channel pitch or a noise period).

    It pairs a read-only integer readout with a text field that accepts an integer or a FamiTracker note
    name, flanked by a :class:`GUIPlusMinusButtons` pair that steps by one and repeats while held. The
    control owns the value it displays, clamps and renders it through its :class:`PitchValueKind`, and
    reports the value through the single ``on_value_changed`` hook once editing settles, so a burst of
    steps collapses into one update. ``set_value`` seeds the readout silently, so a panel can load a
    value and then listen for edits.
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
        plus_minus_layout: PlusMinusButtonsLayout,
        value_color: Color,
    ) -> None:
        self.on_value_changed: Optional[Callable[[int], None]] = None
        self._status_bar = status_bar

        self._tag = tag
        self._parent = parent
        self._kind = kind
        self._layout = layout
        self._plus_minus_layout = plus_minus_layout
        self._label = label
        self._tooltip = tooltip
        self._status_message = status_message
        self._value_color = value_color

        self._value = kind.clamp(initial_value)
        self._emit_token = 0

        self._label_tag = compose_tag(tag, SUF_LABEL)
        self._value_tag = compose_tag(tag, SUF_TEXT)
        self._input_tag = compose_tag(tag, SUF_INPUT)
        self._table_tag = compose_tag(tag, SUF_TABLE)
        self._buttons_tag = compose_tag(tag, SUF_BUTTONS)
        self._tooltip_tag = compose_tag(tag, SUF_TOOLTIP)
        self._input_handler_tag = compose_tag(self._input_tag, SUF_HANDLER_REGISTRY)

        self._buttons: Optional[GUIPlusMinusButtons] = None

        self._build()

    @property
    def value(self) -> int:
        return self._value

    def set_value(self, value: int) -> None:
        """Seeds the displayed value, clamping it into range and rendering it silently."""
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
                with dpg.table_cell() as buttons_cell:
                    self._build_buttons(buttons_cell)

        ThemeRegistry.get(TAG_GLOBAL_THEME_PLUS_MINUS_BUTTONS).bind_to_item(self._table_tag)
        show_tooltip(self._input_tag, self._tooltip, tag=self._tooltip_tag)
        self._status_bar.bind_to_item(self._input_tag, self._status_message)
        self._setup_input_handler()

    def _build_buttons(self, parent: int) -> None:
        buttons = GUIPlusMinusButtons(
            tag=self._buttons_tag,
            parent=parent,
            layout=self._plus_minus_layout,
            order=PlusMinusOrder.MINUS_FIRST,
            hold_repeat=True,
        )
        buttons.on_decrement = self._on_decrement
        buttons.on_increment = self._on_increment
        self._buttons = buttons

    def _clear_existing_items(self) -> None:
        """Removes the widget's own items from a prior build so the control rebuilds cleanly when a panel
        recreates it under the same tags. Deleting the table removes its rows, the readout, the input, and
        the button pair; the tooltip and the input handler registry live outside the table, so they are
        removed on their own. The button pair's own hold handler is cleared when the new pair rebuilds under
        the same tags."""
        for tag in (self._tooltip_tag, self._input_handler_tag, self._table_tag):
            if dpg.does_item_exist(tag):
                dpg_delete_item(tag)

    def _setup_input_handler(self) -> None:
        with dpg.item_handler_registry(tag=self._input_handler_tag):
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_input_committed)

        dpg.bind_item_handler_registry(self._input_tag, self._input_handler_tag)

    def _render(self) -> None:
        dpg_set_value(self._input_tag, self._kind.to_name(self._value))
        dpg_set_value(self._value_tag, str(self._value))

    def _commit(self, value: int) -> None:
        self._value = self._kind.clamp(value)
        self._render()
        self._schedule_emit()

    def _schedule_emit(self) -> None:
        """Renders an update on every step for immediate feedback, reporting the value once the user
        settles. Each change supersedes the previous token, so a burst of steps — including a held
        button — collapses into a single ``on_value_changed`` once the value holds steady for
        ``commit_delay`` frames. The settle posts at ``commit_priority`` (the schedule tier) so it
        orders alongside the debounced regeneration it triggers."""
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

    def _on_decrement(self) -> None:
        self._step(-1)

    def _on_increment(self) -> None:
        self._step(1)

    def _on_input_committed(self, *_arguments: Any) -> None:
        self._apply_text(dpg.get_value(self._input_tag))
