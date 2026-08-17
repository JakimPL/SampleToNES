#!/usr/bin/env python3

"""
Builds the application icon suite into `src/sampletones_assets/icons`.

One geometry definition on a 64-unit grid draws the mark — a smooth sample entering as a
blue sine wave and leaving as an amber square wave, on the studio palette — and every
shipped icon derives from it: the vector `sampletones.svg`, the raster `sampletones.png`,
and the multi-resolution `sampletones.ico`. The raster filenames match the resources the
application resolves through `sampletones_shared/paths`.

Usage:
    python scripts/assets/icons.py            # write the suite into src/sampletones_assets/icons
"""

import argparse
import itertools
import sys
from pathlib import Path
from typing import Final, List, Sequence, Tuple

from PIL import (  # TODO: update THIRD-PARTY-* files, revise LICENSE if still holds
    Image,
    ImageDraw,
)

Point = Tuple[float, float]
Rectangle = Tuple[float, float, float, float]

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
ICONS_DIRECTORY: Final[Path] = PROJECT_ROOT / "src" / "sampletones_assets" / "icons"

# TODO: take the raster filenames from sampletones_shared.paths.resources
VECTOR_FILENAME: Final[str] = "sampletones.svg"
UNIX_ICON_FILENAME: Final[str] = "sampletones.png"
WINDOWS_ICON_FILENAME: Final[str] = "sampletones.ico"

# TODO: SVG configuration should be a YAML file based on a validated Pydantic class
# not a set hardcoded constants; I suggest a nested structure, organizing fields into
# logical units
GRID: Final[int] = 64
CORNER_RADIUS: Final[float] = 14.0
RIM_INSET: Final[float] = 1.0
RIM_WIDTH: Final[float] = 2.0
RIM_OPACITY: Final[float] = 0.14
WAVE_WIDTH: Final[float] = 4.0

BACKGROUND_TOP: Final[str] = "#3a3650"
BACKGROUND_BOTTOM: Final[str] = "#211d30"
SINE_COLOR: Final[str] = "#64c8ff"
SQUARE_COLOR: Final[str] = "#ffc864"
RIM_COLOR: Final[str] = "#cdb6ff"

SINE_START: Final[Point] = (8.0, 32.0)
SINE_CURVES: Final[Tuple[Tuple[Point, Point, Point], ...]] = (
    ((11.0, 16.0), (15.0, 16.0), (18.0, 32.0)),
    ((21.0, 48.0), (25.0, 48.0), (28.0, 32.0)),
)
SQUARE_POINTS: Final[Tuple[Point, ...]] = (
    (28.0, 32.0),
    (28.0, 20.0),
    (38.0, 20.0),
    (38.0, 44.0),
    (48.0, 44.0),
    (48.0, 20.0),
    (56.0, 20.0),
    (56.0, 32.0),
)

SUPERSAMPLE: Final[int] = 16
CURVE_SAMPLES: Final[int] = 96
RASTER_SIZE: Final[int] = 256
ICO_SIZES: Final[Tuple[int, ...]] = (256, 128, 64, 48, 32, 24, 16)


def _grid_number(value: float) -> str:
    return f"{value:g}"


def _sine_path() -> str:
    commands = [f"M{_grid_number(SINE_START[0])} {_grid_number(SINE_START[1])}"]
    for curve in SINE_CURVES:
        points = " ".join(f"{_grid_number(x)} {_grid_number(y)}" for x, y in curve)
        commands.append(f"C{points}")

    return " ".join(commands)


def _square_path() -> str:
    start_x, start_y = SQUARE_POINTS[0]
    commands = [f"M{_grid_number(start_x)} {_grid_number(start_y)}"]
    for (previous_x, _), (x, y) in itertools.pairwise(SQUARE_POINTS):
        commands.append(f"V{_grid_number(y)}" if x == previous_x else f"H{_grid_number(x)}")

    return " ".join(commands)


# TODO: refactor - this should be a proper template as an asset, not hardcoded
def svg_document() -> str:
    """The mark as a standalone vector, with coordinates on the even design grid.

    Grid alignment keeps the wave edges on whole pixels when the icon is rasterized
    at 32 px and 16 px.
    """
    rim_extent = _grid_number(GRID - 2 * RIM_INSET)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}">\n'
        "  <defs>\n"
        '    <linearGradient id="background" x1="0" y1="0" x2="0" y2="1">\n'
        f'      <stop offset="0" stop-color="{BACKGROUND_TOP}"/>\n'
        f'      <stop offset="1" stop-color="{BACKGROUND_BOTTOM}"/>\n'
        "    </linearGradient>\n"
        "  </defs>\n"
        f'  <rect width="{GRID}" height="{GRID}" rx="{_grid_number(CORNER_RADIUS)}" fill="url(#background)"/>\n'
        f'  <path d="{_sine_path()}" fill="none" stroke="{SINE_COLOR}"'
        f' stroke-width="{_grid_number(WAVE_WIDTH)}" stroke-linecap="round"/>\n'
        f'  <path d="{_square_path()}" fill="none" stroke="{SQUARE_COLOR}"'
        f' stroke-width="{_grid_number(WAVE_WIDTH)}"/>\n'
        f'  <rect x="{_grid_number(RIM_INSET)}" y="{_grid_number(RIM_INSET)}"'
        f' width="{rim_extent}" height="{rim_extent}"'
        f' rx="{_grid_number(CORNER_RADIUS - RIM_INSET)}" fill="none" stroke="{RIM_COLOR}"'
        f' stroke-opacity="{RIM_OPACITY}" stroke-width="{_grid_number(RIM_WIDTH)}"/>\n'
        "</svg>\n"
    )


def _background(canvas: int) -> Image.Image:
    top = Image.new("RGB", (canvas, canvas), BACKGROUND_TOP)
    bottom = Image.new("RGB", (canvas, canvas), BACKGROUND_BOTTOM)
    blend = Image.linear_gradient("L").resize((canvas, canvas))
    shaded = Image.composite(bottom, top, blend)

    mask = Image.new("L", (canvas, canvas), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, canvas - 1, canvas - 1),
        radius=CORNER_RADIUS * SUPERSAMPLE,
        fill=255,
    )

    background = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    background.paste(shaded, mask=mask)
    return background


def _cubic_coordinate(
    start: float,
    control_one: float,
    control_two: float,
    end: float,
    progress: float,
) -> float:
    remainder = 1.0 - progress
    return (
        remainder**3 * start
        + 3 * remainder**2 * progress * control_one
        + 3 * remainder * progress**2 * control_two
        + progress**3 * end
    )


def _sine_points() -> List[Point]:
    points: List[Point] = [SINE_START]
    position = SINE_START
    for control_one, control_two, end in SINE_CURVES:
        for step in range(1, CURVE_SAMPLES + 1):
            progress = step / CURVE_SAMPLES
            points.append(
                (
                    _cubic_coordinate(
                        position[0],
                        control_one[0],
                        control_two[0],
                        end[0],
                        progress,
                    ),
                    _cubic_coordinate(
                        position[1],
                        control_one[1],
                        control_two[1],
                        end[1],
                        progress,
                    ),
                )
            )
        position = end

    return points


def _draw_sine(draw: ImageDraw.ImageDraw) -> None:
    """Sweeps a disk of the stroke's half width along the curve.

    The union of densely stamped disks equals a round-capped stroke of the curve and
    keeps the outline smooth, where a single wide polyline call serrates its edges.
    """
    radius = WAVE_WIDTH * SUPERSAMPLE / 2
    for x, y in _sine_points():
        center_x, center_y = x * SUPERSAMPLE, y * SUPERSAMPLE
        draw.ellipse(
            (
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ),
            fill=SINE_COLOR,
        )


def _direction(delta: float) -> float:
    if delta > 0:
        return 1.0

    if delta < 0:
        return -1.0

    return 0.0


def _segment_rectangle(
    start: Point,
    end: Point,
    *,
    half_width: float,
    joined_start: bool,
    joined_end: bool,
) -> Rectangle:
    """The stroke rectangle of one axis-aligned segment.

    A joined end reaches half the stroke width past its corner, so consecutive
    rectangles fill their right-angle miter; an open end keeps a butt cap.
    """
    direction_x = _direction(end[0] - start[0])
    direction_y = _direction(end[1] - start[1])
    start_reach = half_width if joined_start else 0.0
    end_reach = half_width if joined_end else 0.0

    reached_start = (
        start[0] - direction_x * start_reach,
        start[1] - direction_y * start_reach,
    )
    reached_end = (
        end[0] + direction_x * end_reach,
        end[1] + direction_y * end_reach,
    )
    across_x = half_width * abs(direction_y)
    across_y = half_width * abs(direction_x)

    return (
        min(reached_start[0], reached_end[0]) - across_x,
        min(reached_start[1], reached_end[1]) - across_y,
        max(reached_start[0], reached_end[0]) + across_x,
        max(reached_start[1], reached_end[1]) + across_y,
    )


def _square_rectangles() -> List[Rectangle]:
    final_segment = len(SQUARE_POINTS) - 2
    return [
        _segment_rectangle(
            SQUARE_POINTS[index],
            SQUARE_POINTS[index + 1],
            half_width=WAVE_WIDTH / 2,
            joined_start=index > 0,
            joined_end=index < final_segment,
        )
        for index in range(len(SQUARE_POINTS) - 1)
    ]


def _draw_square(draw: ImageDraw.ImageDraw) -> None:
    for left, top, right, bottom in _square_rectangles():
        draw.rectangle(
            (
                round(left * SUPERSAMPLE),
                round(top * SUPERSAMPLE),
                round(right * SUPERSAMPLE) - 1,
                round(bottom * SUPERSAMPLE) - 1,
            ),
            fill=SQUARE_COLOR,
        )


def _rgba(color: str, opacity: float) -> Tuple[int, int, int, int]:
    red, green, blue = (int(color[start : start + 2], 16) for start in (1, 3, 5))
    return red, green, blue, round(opacity * 255)


def _rim_overlay(canvas: int) -> Image.Image:
    overlay = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(
        (0, 0, canvas - 1, canvas - 1),
        radius=CORNER_RADIUS * SUPERSAMPLE,
        outline=_rgba(RIM_COLOR, RIM_OPACITY),
        width=round(RIM_WIDTH * SUPERSAMPLE),
    )
    return overlay


def render_master() -> Image.Image:
    """The mark rasterized at a supersampled resolution, ready to scale down to each shipped size."""
    canvas = GRID * SUPERSAMPLE
    image = _background(canvas)
    draw = ImageDraw.Draw(image)
    _draw_sine(draw)
    _draw_square(draw)
    image.alpha_composite(_rim_overlay(canvas))
    return image


def write_suite(directory: Path) -> List[Path]:
    """Writes the vector, the raster, and the Windows icon into the directory."""
    directory.mkdir(parents=True, exist_ok=True)
    master = render_master()
    renders = {size: master.resize((size, size), Image.Resampling.LANCZOS) for size in ICO_SIZES}

    vector_path = directory / VECTOR_FILENAME
    vector_path.write_text(svg_document(), encoding="utf-8")

    raster_path = directory / UNIX_ICON_FILENAME
    renders[RASTER_SIZE].save(raster_path)

    windows_path = directory / WINDOWS_ICON_FILENAME
    primary, *appended = (renders[size] for size in ICO_SIZES)
    primary.save(
        windows_path,
        format="ICO",
        sizes=[(size, size) for size in ICO_SIZES],
        append_images=appended,
    )

    return [vector_path, raster_path, windows_path]


# TODO: this file should be only a thin layer, the rest of the code
# should belong to sampletones_assets
# Read guidelines and architecture docs, follow the current code philosophy
def main(argv: Sequence[str]) -> int:
    """Writes the icon suite and reports each file it produced."""

    parser = argparse.ArgumentParser(
        description="Build the application icon suite from the mark's geometry.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=ICONS_DIRECTORY,
        help="directory receiving the icon files",
    )
    arguments = parser.parse_args(list(argv))

    for path in write_suite(arguments.directory):
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
