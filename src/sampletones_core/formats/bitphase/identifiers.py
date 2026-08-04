from sampletones_core.formats.bitphase.specification.instruments import INSTRUMENT_ID_DIGITS
from sampletones_core.formats.bitphase.specification.patterns import SYMBOL_BASE, SYMBOL_DIGITS


def format_instrument_id(number: int) -> str:
    """Renders an instrument number as the base-36 text a pattern column matches on.

    Args:
        number: Instrument number, at most :data:`MAX_INSTRUMENT_ID`.

    Returns:
        str: The number in base 36, padded to the width of the instrument column.
    """
    digits = ""
    remaining = number
    for _ in range(INSTRUMENT_ID_DIGITS):
        remaining, digit = divmod(remaining, SYMBOL_BASE)
        digits = SYMBOL_DIGITS[digit] + digits

    return digits
