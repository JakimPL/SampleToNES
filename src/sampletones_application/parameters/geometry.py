from __future__ import annotations

from dataclasses import dataclass

from sampletones_application.layout.config import LayoutConfig


@dataclass(frozen=True)
class TabGeometry:
    """The geometry every tab coordinator lays its columns out on.

    These six values are identical across all four tabs: the uniform side column's
    size, the responsive baseline and centre share that drive its width as the
    viewport grows, the rail it docks to when collapsed, and the gap between panels.
    They are flattened to scalars because each feeds a pure-int sink
    (``expanded_side_width``, ``ColumnSpec``, raw ``dpg.configure_item``) that blends
    the configured value with a live viewport measurement.
    """

    side_width: int
    side_height: int
    center_weight: int
    baseline_viewport_width: int
    rail_width: int
    panel_gap: int

    @classmethod
    def from_config(cls, config: LayoutConfig) -> TabGeometry:
        general = config.general
        return cls(
            side_width=general.columns.side.width,
            side_height=general.columns.side.height,
            center_weight=general.columns.center_weight,
            baseline_viewport_width=general.responsive.baseline_viewport_width,
            rail_width=general.collapse.rail_width,
            panel_gap=general.panel_gap,
        )
