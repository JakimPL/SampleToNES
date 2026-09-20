from enum import StrEnum
from typing import Sequence, Tuple

from sampletones_tools.codec.study.packing.coding import PlaneCoding
from sampletones_tools.codec.study.packing.fitted import FORM_SIZE, fitted_form
from sampletones_tools.codec.study.packing.registers import register_forms
from sampletones_tools.codec.study.packing.table import TableForm


class PackingScheme(StrEnum):
    """Where a plane's division between its value and its repeat count comes from.

    Attributes:
        FIXED: The bits the plane's own register leaves alone, which every song shares, so the
            block states nothing and the driver knows each plane's mask by the plane it is.
        FITTED: The bits the song's own values leave alone, which reaches further and which the
            block states as a mask and the bits the register fixes.
        TABLE: The plane's distinct values gathered into a table the block states, which reaches
            a plane whose values spread across its byte.
    """

    FIXED = "fixed"
    FITTED = "fitted"
    TABLE = "table"


def plane_codings(
    planes: Sequence[bytes],
    scheme: PackingScheme,
) -> Tuple[PlaneCoding, ...]:
    """How each plane's byte divides under a scheme.

    Args:
        planes: The planes, in the order the song block writes them.
        scheme: Where the division comes from.

    Returns:
        Tuple[PlaneCoding, ...]: One coding per plane, in the order given.
    """
    match scheme:
        case PackingScheme.FIXED:
            return tuple(register_forms())
        case PackingScheme.FITTED:
            return tuple(fitted_form(plane) for plane in planes)
        case PackingScheme.TABLE:
            return tuple(_table(plane) for plane in planes)


def stated_bytes(
    codings: Sequence[PlaneCoding],
    scheme: PackingScheme,
) -> int:
    """The bytes the song block takes to state how its planes are read.

    Args:
        codings: How each plane's byte divides.
        scheme: Where the division comes from.

    Returns:
        int: The bytes the block states beyond what it states today.
    """
    match scheme:
        case PackingScheme.FIXED:
            return 0
        case PackingScheme.FITTED:
            return FORM_SIZE * len(codings)
        case PackingScheme.TABLE:
            return sum(coding.stated for coding in codings if isinstance(coding, TableForm))


def _table(plane: bytes) -> PlaneCoding:
    if not plane:
        return fitted_form(plane)

    return TableForm.across(plane)
