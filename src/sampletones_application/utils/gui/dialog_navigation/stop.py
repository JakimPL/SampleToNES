from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sampletones_application.tags.general import SUF_BUTTON, TAG_GLOBAL_THEME_DEFAULT
from sampletones_shared.types.callback import VoidCallback


@dataclass(frozen=True)
class FocusStop:
    """One stop in a dialog's focus ring.

    ``focus_tag`` is the item :func:`dpg.focus_item` targets, ``enabled_tag`` the item whose
    enabled state gates the stop, and ``activate`` the Enter action for a button. Fields and
    combos leave ``activate`` empty so Enter stays with the control (Enter in the multiline
    comment inserts a line break, and a text-input dialog keeps its own submit-on-Enter).
    ``base_theme_tag`` names the theme a button wears while unfocused; the ring rebinds it once
    the focus outline moves on. Fields leave it empty, marking them as stops the ring styles by
    their own edit caret rather than an outline.
    """

    focus_tag: str
    enabled_tag: str
    activate: Optional[VoidCallback]
    base_theme_tag: Optional[str] = None

    @classmethod
    def button(
        cls,
        tag: str,
        activate: VoidCallback,
        *,
        base_theme_tag: str = TAG_GLOBAL_THEME_DEFAULT,
    ) -> FocusStop:
        """Builds a stop for a :class:`GUIButton`, focusing its inner button item.

        ``base_theme_tag`` is the button's own theme, which the ring rebinds when the focus
        outline leaves the button.
        """
        return cls(
            focus_tag=f"{tag}{SUF_BUTTON}",
            enabled_tag=tag,
            activate=activate,
            base_theme_tag=base_theme_tag,
        )

    @classmethod
    def field(cls, tag: str) -> FocusStop:
        """Builds a stop for a text field or combo, which owns Enter itself."""
        return cls(
            focus_tag=tag,
            enabled_tag=tag,
            activate=None,
        )
