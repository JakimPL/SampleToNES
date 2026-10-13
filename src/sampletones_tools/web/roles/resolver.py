from dataclasses import dataclass
from typing import Dict

from sampletones_shared.types.application import ColorRGBA
from sampletones_tools.web.design import ApplicationDesign
from sampletones_tools.web.roles.table import COLOR_ROLES, DIMENSION_ROLES


@dataclass(frozen=True)
class RoleSheet:
    """Every role resolved in one design: colors, and sizes in application pixels."""

    colors: Dict[str, ColorRGBA]
    dimensions: Dict[str, float]


def resolve_roles(design: ApplicationDesign) -> RoleSheet:
    """Every role of the table, read from ``design``.

    Raises:
        KeyError: If a role names a theme entry the configuration does not state.
    """
    return RoleSheet(
        colors={name: role.resolve(design) for name, role in COLOR_ROLES.items()},
        dimensions={name: role.resolve(design) for name, role in DIMENSION_ROLES.items()},
    )
