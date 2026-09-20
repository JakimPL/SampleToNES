from typing import Dict, Final, Tuple

from sampletones_core.constants.general import MAX_DUTY_CYCLE, MAX_PERIOD, MAX_VOLUME
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.registers import (
    DUTY_CYCLE_SHIFT,
    NOISE_MODE_SHIFT,
    SUSTAINED_LEVEL,
)
from sampletones_tools.codec.study.packing.form import NO_BITS, WHOLE_BYTE, PlaneForm

DUTY_CYCLE_FIELD: Final[int] = MAX_DUTY_CYCLE << DUTY_CYCLE_SHIFT
VOLUME_FIELD: Final[int] = MAX_VOLUME
PERIOD_FIELD: Final[int] = MAX_PERIOD
NOISE_MODE_FIELD: Final[int] = 1 << NOISE_MODE_SHIFT

PULSE_CONTROL_FORM: Final[PlaneForm] = PlaneForm(
    value_mask=DUTY_CYCLE_FIELD | VOLUME_FIELD,
    value_or=SUSTAINED_LEVEL,
)
NOISE_CONTROL_FORM: Final[PlaneForm] = PlaneForm(
    value_mask=VOLUME_FIELD,
    value_or=SUSTAINED_LEVEL,
)
NOISE_VALUE_FORM: Final[PlaneForm] = PlaneForm(
    value_mask=NOISE_MODE_FIELD | PERIOD_FIELD,
    value_or=NO_BITS,
)

PLANE_FORMS: Final[Dict[str, PlaneForm]] = {
    "pulse1_control": PULSE_CONTROL_FORM,
    "pulse1_value": WHOLE_BYTE,
    "pulse1_bend": WHOLE_BYTE,
    "pulse2_control": PULSE_CONTROL_FORM,
    "pulse2_value": WHOLE_BYTE,
    "pulse2_bend": WHOLE_BYTE,
    "triangle_control": WHOLE_BYTE,
    "triangle_value": WHOLE_BYTE,
    "triangle_bend": WHOLE_BYTE,
    "noise_control": NOISE_CONTROL_FORM,
    "noise_value": NOISE_VALUE_FORM,
}


def register_forms() -> Tuple[PlaneForm, ...]:
    """The form each plane's own register fixes, in the order the song block writes the planes.

    A pulse channel's control byte holds its duty cycle and volume around two bits the hardware
    wants set, a noise channel's control byte holds a volume under the same two, and a noise
    period byte holds a mode bit above three the register reads nothing from. Those are the bits
    a repeat count rides in without the block stating anything. Every other plane spends its
    whole byte, so it reads as it does today.

    Returns:
        Tuple[PlaneForm, ...]: One form per plane, in song-block order.

    Raises:
        KeyError: If a plane the song block writes names no form.
    """
    return tuple(PLANE_FORMS[name] for name in PlaneOrder.names())
