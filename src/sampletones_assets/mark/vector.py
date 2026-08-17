import itertools
from string import Template
from typing import Dict

from sampletones_assets.mark.paths import TEMPLATE_PATH
from sampletones_assets.mark.specification import Mark
from sampletones_assets.mark.specification.point import Point
from sampletones_assets.mark.specification.waves import MarkSine, MarkSquare


def _number(value: float) -> str:
    return f"{value:g}"


def _coordinates(point: Point) -> str:
    return f"{_number(point.x)} {_number(point.y)}"


def _sine_path(sine: MarkSine) -> str:
    commands = [f"M{_coordinates(sine.start)}"]
    for curve in sine.curves:
        controls = f"{_coordinates(curve.control_start)} {_coordinates(curve.control_end)}"
        commands.append(f"C{controls} {_coordinates(curve.end)}")

    return " ".join(commands)


def _square_path(square: MarkSquare) -> str:
    """The stepped half as vertical and horizontal commands, one per segment.

    Each segment turns on a single axis, so it is written as the one coordinate it moves
    along and the renderer holds the other.
    """
    commands = [f"M{_coordinates(square.points[0])}"]
    for previous, point in itertools.pairwise(square.points):
        commands.append(f"V{_number(point.y)}" if point.x == previous.x else f"H{_number(point.x)}")

    return " ".join(commands)


def _placeholders(mark: Mark) -> Dict[str, str]:
    return {
        "grid": _number(mark.frame.grid),
        "corner_radius": _number(mark.frame.corner_radius),
        "background_top": mark.colors.background.top,
        "background_bottom": mark.colors.background.bottom,
        "sine_path": _sine_path(mark.waves.sine),
        "sine_color": mark.colors.sine,
        "square_path": _square_path(mark.waves.square),
        "square_color": mark.colors.square,
        "wave_width": _number(mark.waves.width),
        "rim_inset": _number(mark.frame.rim.inset),
        "rim_extent": _number(mark.frame.rim_extent),
        "rim_radius": _number(mark.frame.rim_radius),
        "rim_color": mark.colors.rim,
        "rim_opacity": _number(mark.frame.rim.opacity),
        "rim_width": _number(mark.frame.rim.width),
    }


def render_vector(mark: Mark) -> str:
    """The mark as a standalone vector, filling the packaged template with its own geometry.

    Coordinates stay on the design grid, which keeps the wave edges on whole pixels when the
    icon is rasterized at 32 px and 16 px.

    Raises:
        KeyError: If the template names a placeholder the mark leaves unfilled.
    """
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.substitute(_placeholders(mark))
