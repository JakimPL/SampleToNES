from typing import Annotated, Union

from pydantic import Field

from .exponential_glide import ExponentialGlideOscillator
from .geometric_sweep import GeometricSweepOscillator
from .pulse import PulseOscillator
from .sine import SineOscillator
from .walk_noise import WalkNoiseOscillator
from .white_noise import WhiteNoiseOscillator

OscillatorUnion = Annotated[
    Union[
        SineOscillator,
        GeometricSweepOscillator,
        ExponentialGlideOscillator,
        PulseOscillator,
        WhiteNoiseOscillator,
        WalkNoiseOscillator,
    ],
    Field(discriminator="kind"),
]
