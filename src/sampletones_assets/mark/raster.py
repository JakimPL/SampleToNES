from typing import Final, Tuple

from PIL import Image, ImageDraw  # TODO: update THIRD-PARTY-* files, revise LICENSE if still holds

from sampletones_assets.mark.geometry import sine_points, square_rectangles
from sampletones_assets.mark.specification import Mark
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import parse_hex_color, with_alpha_fraction

TRANSPARENT: Final[ColorRGBA] = (0, 0, 0, 0)
OPAQUE: Final[int] = 255


class MarkRaster:
    """Draws the mark into one supersampled image, ready to scale down to each shipped size.

    Drawing happens at the render factor times the design grid and the result is resampled
    down, which is what keeps the curve edges and the rounded corners smooth at 16 px.
    """

    def __init__(self, mark: Mark) -> None:
        self.mark = mark

    @property
    def scale(self) -> int:
        """Factor the design grid is drawn at."""
        return self.mark.render.supersample

    @property
    def canvas(self) -> int:
        """Edge length in pixels of the image the mark is drawn into."""
        return self.mark.frame.grid * self.scale

    @property
    def corner_radius(self) -> float:
        """Corner radius of the frame, in the pixels of the drawn image."""
        return self.mark.frame.corner_radius * self.scale

    @property
    def frame_box(self) -> Tuple[int, int, int, int]:
        """The whole image, as the box the frame and its rim are drawn in."""
        return (0, 0, self.canvas - 1, self.canvas - 1)

    def render(self) -> Image.Image:
        """The mark drawn at the supersampled resolution, on a transparent ground."""
        image = self._background()
        draw = ImageDraw.Draw(image)
        self._draw_sine(draw)
        self._draw_square(draw)
        image.alpha_composite(self._rim())
        return image

    def _background(self) -> Image.Image:
        """The frame: a vertical gradient between the two background colours, rounded at its corners."""
        size = (self.canvas, self.canvas)
        top = Image.new("RGB", size, self.mark.colors.background.top)
        bottom = Image.new("RGB", size, self.mark.colors.background.bottom)
        shaded = Image.composite(bottom, top, Image.linear_gradient("L").resize(size))

        background = Image.new("RGBA", size, TRANSPARENT)
        background.paste(shaded, mask=self._frame_mask())
        return background

    def _frame_mask(self) -> Image.Image:
        mask = Image.new("L", (self.canvas, self.canvas), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            self.frame_box,
            radius=self.corner_radius,
            fill=OPAQUE,
        )
        return mask

    def _draw_sine(self, draw: ImageDraw.ImageDraw) -> None:
        """Sweeps a disk of the stroke's half width along the curve.

        The union of densely stamped disks equals a round-capped stroke of the curve, which is
        what holds the outline smooth along its whole sweep.
        """
        radius = self.mark.waves.width * self.scale / 2
        for point in sine_points(self.mark.waves.sine, self.mark.render.curve_samples):
            center_x, center_y = point.x * self.scale, point.y * self.scale
            draw.ellipse(
                (
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                ),
                fill=self.mark.colors.sine,
            )

    def _draw_square(self, draw: ImageDraw.ImageDraw) -> None:
        for rectangle in square_rectangles(self.mark.waves.square, self.mark.waves.width):
            draw.rectangle(
                (
                    round(rectangle.left * self.scale),
                    round(rectangle.top * self.scale),
                    round(rectangle.right * self.scale) - 1,
                    round(rectangle.bottom * self.scale) - 1,
                ),
                fill=self.mark.colors.square,
            )

    def _rim(self) -> Image.Image:
        """The hairline along the frame's edge, as a layer to composite over the drawn mark."""
        overlay = Image.new("RGBA", (self.canvas, self.canvas), TRANSPARENT)
        ImageDraw.Draw(overlay).rounded_rectangle(
            self.frame_box,
            radius=self.corner_radius,
            outline=self._rim_color(),
            width=round(self.mark.frame.rim.width * self.scale),
        )
        return overlay

    def _rim_color(self) -> ColorRGBA:
        return with_alpha_fraction(parse_hex_color(self.mark.colors.rim), self.mark.frame.rim.opacity)
