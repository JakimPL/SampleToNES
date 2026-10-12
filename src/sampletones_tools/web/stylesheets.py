from typing import Dict, Final, List

from sampletones_tools.web.colors import color_scheme, css_color
from sampletones_tools.web.fonts import FONT_STACKS
from sampletones_tools.web.roles.resolver import RoleSheet

GROUND_ROLE: Final[str] = "ground"
SIZE_PREFIX: Final[str] = "size-"
FONT_PREFIX: Final[str] = "font-"


def roles_stylesheet(
    sheet: RoleSheet,
    sizes: Dict[str, float],
) -> str:
    """The roles, sizes and font stacks as custom properties on ``:root``.

    Colors are written as hexadecimal, sizes in pixels, and the color scheme follows the ground,
    so a page's form controls and scrollbars stand on it as the rest does.
    """
    declarations: List[str] = [f"color-scheme: {color_scheme(sheet.colors[GROUND_ROLE])};"]
    declarations.extend(f"--{name}: {css_color(color)};" for name, color in sorted(sheet.colors.items()))
    declarations.extend(f"--{name}: {_pixels(value)};" for name, value in sorted(sheet.dimensions.items()))
    declarations.extend(f"--{SIZE_PREFIX}{name}: {_pixels(value)};" for name, value in sorted(sizes.items()))
    declarations.extend(f"--{FONT_PREFIX}{typeface.value}: {stack};" for typeface, stack in FONT_STACKS.items())
    body = "".join(f"  {declaration}\n" for declaration in declarations)
    return f":root {{\n{body}}}\n"


def _pixels(value: float) -> str:
    return f"{value:g}px"
