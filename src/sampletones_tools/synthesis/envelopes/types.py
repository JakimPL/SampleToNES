from typing import Annotated, Union

from pydantic import Field

from .exponential_decay import ExponentialDecayEnvelope
from .gate import GateEnvelope
from .linear_attack import LinearAttackEnvelope
from .linear_ramp import LinearRampEnvelope
from .periodic_decay import PeriodicDecayEnvelope

EnvelopeUnion = Annotated[
    Union[
        ExponentialDecayEnvelope,
        GateEnvelope,
        LinearAttackEnvelope,
        LinearRampEnvelope,
        PeriodicDecayEnvelope,
    ],
    Field(discriminator="kind"),
]
