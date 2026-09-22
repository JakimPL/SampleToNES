from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_FOCUSED_BUTTON,
)
from sampletones_shared.types.callback import VoidCallback


@dataclass(frozen=True)
class FocusStop:
    """One stop in a dialog's focus ring.

    ``focus_tag`` is the item :func:`dpg.focus_item` targets, ``enabled_tag`` the item whose
    enabled state gates the stop, and ``activate`` the Enter action for a button. Fields and
    combos leave ``activate`` empty so Enter stays with the control (Enter in the multiline
    comment inserts a line break, and a text-input dialog keeps its own submit-on-Enter).
    ``base_theme_tag`` names the theme a button wears while unfocused; the ring rebinds it once
    the focus outline moves on. ``focused_theme_tag`` names the theme it wears while focused,
    which carries the base theme's own colors forward under the accent border, since a bound
    theme replaces a button's colors outright rather than layering over another bind. Fields
    leave both empty, marking them as stops the ring styles by their own edit caret.
    """

    focus_tag: str
    enabled_tag: str
    activate: Optional[VoidCallback]
    base_theme_tag: Optional[str] = None
    focused_theme_tag: Optional[str] = None

    @classmethod
    def button(
        cls,
        tag: str,
        activate: VoidCallback,
        *,
        base_theme_tag: str = TAG_GLOBAL_THEME_DEFAULT,
        focused_theme_tag: str = TAG_GLOBAL_THEME_FOCUSED_BUTTON,
    ) -> FocusStop:
        """Builds a stop for a :class:`GUIButton`, focusing its inner button item.

        ``base_theme_tag`` is the button's own theme, which the ring rebinds when the focus
        outline leaves the button. A button carrying a theme of its own beyond the default,
        such as a danger button, passes the matching ``focused_theme_tag`` too, which is that
        same theme with the accent border added, so the button keeps its own color while it
        holds focus rather than reading as an unstyled default button.
        """
        return cls(
            focus_tag=compose_tag(tag, SUF_BUTTON),
            enabled_tag=tag,
            activate=activate,
            base_theme_tag=base_theme_tag,
            focused_theme_tag=focused_theme_tag,
        )

    @classmethod
    def field(cls, tag: str) -> FocusStop:
        """Builds a stop for a text field or combo, which owns Enter itself."""
        return cls(
            focus_tag=tag,
            enabled_tag=tag,
            activate=None,
        )
