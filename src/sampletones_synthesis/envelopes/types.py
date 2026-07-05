from typing import Annotated, Union

from pydantic import Field

from .exponential_decay import ExponentialDecayEnvelope
from .linear_attack import LinearAttackEnvelope
from .linear_ramp import LinearRampEnvelope

EnvelopeUnion = Annotated[
    Union[
        ExponentialDecayEnvelope,
        LinearAttackEnvelope,
        LinearRampEnvelope,
    ],
    Field(discriminator="kind"),
]
