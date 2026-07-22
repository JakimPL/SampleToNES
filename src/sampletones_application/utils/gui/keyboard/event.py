from __future__ import annotations

from dataclasses import dataclass

import dearpygui.dearpygui as dpg


@dataclass(frozen=True)
class KeyEvent:
    """A key press together with the modifier state captured at the moment it fired.

    The router snapshots the modifiers once per event, so every scope reads the same
    ``ctrl``/``shift``/``alt`` state.
    """

    key: int
    ctrl: bool
    shift: bool
    alt: bool

    @classmethod
    def capture(cls, key: int) -> KeyEvent:
        """Builds an event for ``key`` with the modifier keys currently held."""
        return cls(
            key=key,
            ctrl=dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl),
            shift=dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift),
            alt=dpg.is_key_down(dpg.mvKey_LAlt) or dpg.is_key_down(dpg.mvKey_RAlt),
        )
