from typing import List, Optional, Self

from pydantic import BaseModel, Field
from screeninfo import Monitor, ScreenInfoError, get_monitors

from sampletones_shared.display import Resolution
from sampletones_shared.logger import logger


class MonitorArea(BaseModel, frozen=True):
    """The rectangle a monitor occupies, and how much of it a window may take.

    A window keeps a margin of the monitor free so its decoration frame stays on screen, which
    makes :attr:`usable_width` and :attr:`usable_height` the size a window is fitted to and the
    ceiling a selectable resolution is measured against. The fraction is carried with the area,
    so the window layout that sets the margin decides it for every area it builds.
    """

    x: int
    y: int
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    usable_ratio: float = Field(gt=0.0, le=1.0)

    @property
    def usable_width(self) -> int:
        return int(self.width * self.usable_ratio)

    @property
    def usable_height(self) -> int:
        return int(self.height * self.usable_ratio)

    @classmethod
    def of(cls, monitor: Monitor, usable_ratio: float) -> Self:
        return cls(
            x=int(monitor.x),
            y=int(monitor.y),
            width=int(monitor.width),
            height=int(monitor.height),
            usable_ratio=usable_ratio,
        )

    @classmethod
    def assumed(cls, monitor: Resolution, usable_ratio: float) -> Self:
        """The area a window is fitted to against a monitor size the caller assumes."""
        return cls(
            x=0,
            y=0,
            width=monitor.width,
            height=monitor.height,
            usable_ratio=usable_ratio,
        )


def available_monitors() -> List[Monitor]:
    """Monitors reported by the platform, empty where none can be enumerated.

    A display server that exposes no enumerator — a headless session, a remote shell, a Wayland
    compositor without the expected backend — makes ``screeninfo`` raise instead of returning an
    empty list, so a caller falls back to assumed dimensions.
    """
    try:
        return get_monitors()
    except ScreenInfoError as exception:
        logger.warning(f"No monitor information available: {exception}")
        return []


def monitor_for_window(
    x: int,
    y: int,
    width: int,
    height: int,
) -> Optional[Monitor]:
    """The monitor a window overlaps most, or nothing while the platform reports none."""
    monitors = available_monitors()
    if not monitors:
        return None

    return max(
        monitors,
        key=lambda monitor: _overlap(monitor, x, y, width, height),
    )


def monitor_area_for_window(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    usable_ratio: float,
    fallback_monitor: Resolution,
) -> MonitorArea:
    """The area of the monitor a window sits on, the given size where the platform reports none."""
    monitor = monitor_for_window(x, y, width, height)
    if monitor is None:
        return MonitorArea.assumed(fallback_monitor, usable_ratio)

    return MonitorArea.of(monitor, usable_ratio)


def _overlap(
    monitor: Monitor,
    x: int,
    y: int,
    width: int,
    height: int,
) -> int:
    overlap_width = max(0, min(x + width, monitor.x + monitor.width) - max(x, monitor.x))
    overlap_height = max(0, min(y + height, monitor.y + monitor.height) - max(y, monitor.y))
    return int(overlap_width * overlap_height)
