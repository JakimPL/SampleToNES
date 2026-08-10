from __future__ import annotations

from typing import Dict, Tuple

from pydantic import BaseModel

from sampletones_shared.display import UNLIMITED_FRAME_RATE, Resolution


def available_resolutions(
    resolutions: Tuple[Resolution, ...],
    *,
    min_width: int,
    min_height: int,
    max_width: int,
    max_height: int,
) -> Tuple[Resolution, ...]:
    """The sizes a window may open at within the given bounds, in the order they are offered.

    A size is offered when it meets the window's minimum and stays inside the bound the caller
    measures against — the usable area of the monitor the window sits on — so the window opens
    at the size that was picked and comes back at it after a restart. The monitor's own
    resolution is reached by going fullscreen.

    Args:
        resolutions: The sizes the build offers, in the order a combo shows them.
        min_width: Narrowest width the window opens at.
        min_height: Shortest height the window opens at.
        max_width: Widest width the window is given room for.
        max_height: Tallest height the window is given room for.

    Returns:
        Tuple[Resolution, ...]: The sizes to offer, or the window minimum alone where the bounds
            leave room for none of them.
    """
    offered = tuple(
        resolution
        for resolution in resolutions
        if resolution.reaches(min_width, min_height) and resolution.fits_within(max_width, max_height)
    )
    if offered:
        return offered

    return (Resolution(width=min_width, height=min_height),)


def resolution_labels(resolutions: Tuple[Resolution, ...]) -> Tuple[str, ...]:
    return tuple(str(resolution) for resolution in resolutions)


def frame_rate_label(frame_rate: int, *, unlimited_label: str) -> str:
    """The label a frame rate shows under, naming zero as the unlimited setting."""
    return unlimited_label if frame_rate == UNLIMITED_FRAME_RATE else str(frame_rate)


def frame_rate_labels(frame_rates: Tuple[int, ...], *, unlimited_label: str) -> Tuple[str, ...]:
    return tuple(frame_rate_label(frame_rate, unlimited_label=unlimited_label) for frame_rate in frame_rates)


def nearest_frame_rate(max_fps: int, frame_rates: Tuple[int, ...]) -> int:
    """The offered frame rate a stored preference selects, the closest one it lies between.

    A preference outlives the list that was offered when it was written, so a stored value the
    build has since dropped still selects an entry the combo shows.

    Raises:
        ValueError: when no frame rate is offered.
    """
    if not frame_rates:
        raise ValueError("Selecting a frame rate requires at least one offered rate")

    if max_fps in frame_rates:
        return max_fps

    return min(frame_rates, key=lambda frame_rate: (abs(frame_rate - max_fps), frame_rate))


def nearest_resolution(
    width: int,
    height: int,
    resolutions: Tuple[Resolution, ...],
) -> Resolution:
    """The offered size a window of the given dimensions selects, the closest one by area.

    Raises:
        ValueError: when no size is offered.
    """
    if not resolutions:
        raise ValueError("Selecting a resolution requires at least one offered size")

    return min(
        resolutions,
        key=lambda resolution: (
            abs(resolution.width - width) + abs(resolution.height - height),
            resolution.width,
            resolution.height,
        ),
    )


class WindowMode(BaseModel, frozen=True):
    """How the window presents itself on its monitor: the size it takes and the frame around it.

    The three settings decide together whether the window stays usable, so they travel as one
    value: a change to any of them is what a revert countdown guards, and restoring the mode
    puts all three back at once. Each ``with_`` method answers with the mode carrying one
    setting changed, leaving the mode it was asked of intact.
    """

    resolution: Resolution
    borderless: bool
    fullscreen: bool

    def with_resolution(self, resolution: Resolution) -> WindowMode:
        return self.model_copy(update={"resolution": resolution})

    def with_borderless(self, borderless: bool) -> WindowMode:
        return self.model_copy(update={"borderless": borderless})

    def with_fullscreen(self, fullscreen: bool) -> WindowMode:
        return self.model_copy(update={"fullscreen": fullscreen})


class DisplaySettings(BaseModel, frozen=True):
    """Everything the display settings offer, as one value to compare, snapshot and restore.

    The dialog edits a copy and applies it live while the session keeps the values it opened
    with, so a snapshot taken at that moment restores the appearance a user came in with. Each
    ``with_`` method answers with the settings carrying one entry changed.
    """

    palette: str
    window: WindowMode
    vsync: bool
    frame_rate: int

    def with_palette(self, palette: str) -> DisplaySettings:
        return self.model_copy(update={"palette": palette})

    def with_window(self, window: WindowMode) -> DisplaySettings:
        return self.model_copy(update={"window": window})

    def with_vsync(self, vsync: bool) -> DisplaySettings:
        return self.model_copy(update={"vsync": vsync})

    def with_frame_rate(self, frame_rate: int) -> DisplaySettings:
        return self.model_copy(update={"frame_rate": frame_rate})


class DisplaySettingsViewModel(BaseModel, frozen=True):
    """What the display settings dialog draws: the options offered, and the selection standing.

    The sizes are those the window's monitor leaves room for, so the offer follows the screen the
    window sits on. Each combo reads its labels here and reports a chosen label back, keeping the
    projection between a label and the value it stands for in one place.
    """

    settings: DisplaySettings
    resolutions: Tuple[Resolution, ...]
    frame_rates: Tuple[int, ...]
    palettes: Tuple[str, ...]

    @classmethod
    def build(
        cls,
        settings: DisplaySettings,
        *,
        resolutions: Tuple[Resolution, ...],
        frame_rates: Tuple[int, ...],
        palettes: Tuple[str, ...],
        min_width: int,
        min_height: int,
        max_width: int,
        max_height: int,
    ) -> DisplaySettingsViewModel:
        """Offers what the given bounds leave room for, with the standing selection snapped onto it.

        A window sized between two offered entries — restored from a session, or dragged to a size
        of its own — selects the nearest one, so the combos always show the state that is in force.

        Args:
            settings: The display state in force.
            resolutions: The sizes the build offers.
            frame_rates: The frame rates the build offers.
            palettes: The palettes the build ships, in the order they are offered.
            min_width: Narrowest width the window opens at.
            min_height: Shortest height the window opens at.
            max_width: Widest width the window's monitor leaves room for.
            max_height: Tallest height the window's monitor leaves room for.
        """
        offered = available_resolutions(
            resolutions,
            min_width=min_width,
            min_height=min_height,
            max_width=max_width,
            max_height=max_height,
        )
        selected = WindowMode(
            resolution=nearest_resolution(
                settings.window.resolution.width,
                settings.window.resolution.height,
                offered,
            ),
            borderless=settings.window.borderless,
            fullscreen=settings.window.fullscreen,
        )
        return cls(
            settings=DisplaySettings(
                palette=settings.palette,
                window=selected,
                vsync=settings.vsync,
                frame_rate=nearest_frame_rate(settings.frame_rate, frame_rates),
            ),
            resolutions=offered,
            frame_rates=frame_rates,
            palettes=palettes,
        )

    @property
    def window_controls_enabled(self) -> bool:
        """Whether the size and frame controls apply: a fullscreen window takes its whole monitor."""
        return not self.settings.window.fullscreen

    @property
    def resolution_items(self) -> Tuple[str, ...]:
        return resolution_labels(self.resolutions)

    @property
    def current_resolution_item(self) -> str:
        return str(self.settings.window.resolution)

    def frame_rate_items(self, unlimited_label: str) -> Tuple[str, ...]:
        return frame_rate_labels(self.frame_rates, unlimited_label=unlimited_label)

    def current_frame_rate_item(self, unlimited_label: str) -> str:
        return frame_rate_label(self.settings.frame_rate, unlimited_label=unlimited_label)

    def resolution_for_item(self, item: str) -> Resolution:
        """The size the given label stands for.

        Raises:
            KeyError: when no offered size carries that label.
        """
        offered: Dict[str, Resolution] = {str(resolution): resolution for resolution in self.resolutions}
        return offered[item]

    def frame_rate_for_item(self, item: str, unlimited_label: str) -> int:
        """The frame rate the given label stands for.

        Raises:
            KeyError: when no offered rate carries that label.
        """
        offered: Dict[str, int] = {
            frame_rate_label(frame_rate, unlimited_label=unlimited_label): frame_rate for frame_rate in self.frame_rates
        }
        return offered[item]
