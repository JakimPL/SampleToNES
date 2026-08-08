from dataclasses import dataclass
from typing import Any, Dict, Final, Tuple, Type

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from sampletones_synthesis.envelopes.exponential_decay import ExponentialDecayEnvelope
from sampletones_synthesis.envelopes.linear_attack import LinearAttackEnvelope
from sampletones_synthesis.envelopes.linear_ramp import LinearRampEnvelope
from sampletones_synthesis.envelopes.types import EnvelopeUnion
from sampletones_synthesis.oscillators.exponential_glide import ExponentialGlideOscillator
from sampletones_synthesis.oscillators.geometric_sweep import GeometricSweepOscillator
from sampletones_synthesis.oscillators.pulse import PulseOscillator
from sampletones_synthesis.oscillators.sine import SineOscillator
from sampletones_synthesis.oscillators.types import OscillatorUnion
from sampletones_synthesis.oscillators.walk_noise import WalkNoiseOscillator
from sampletones_synthesis.oscillators.white_noise import WhiteNoiseOscillator

OSCILLATOR_ADAPTER: Final[TypeAdapter[Any]] = TypeAdapter(OscillatorUnion)
ENVELOPE_ADAPTER: Final[TypeAdapter[Any]] = TypeAdapter(EnvelopeUnion)


@dataclass(frozen=True)
class DiscriminationCase:
    name: str
    adapter: TypeAdapter[Any]
    payload: Dict[str, Any]
    expected_type: Type[BaseModel]


DISCRIMINATION_CASES: Final[Tuple[DiscriminationCase, ...]] = (
    DiscriminationCase(
        name="sine",
        adapter=OSCILLATOR_ADAPTER,
        payload={"kind": "sine", "frequency": 440.0},
        expected_type=SineOscillator,
    ),
    DiscriminationCase(
        name="geometric_sweep",
        adapter=OSCILLATOR_ADAPTER,
        payload={
            "kind": "geometric_sweep",
            "frequency_start": 67,
            "frequency_end": 29,
        },
        expected_type=GeometricSweepOscillator,
    ),
    DiscriminationCase(
        name="exponential_glide",
        adapter=OSCILLATOR_ADAPTER,
        payload={
            "kind": "exponential_glide",
            "frequency_start": 150.0,
            "frequency_end": 50.0,
            "time_constant_seconds": 0.25,
        },
        expected_type=ExponentialGlideOscillator,
    ),
    DiscriminationCase(
        name="pulse",
        adapter=OSCILLATOR_ADAPTER,
        payload={"kind": "pulse", "frequency": 220.0, "duty_cycle": 0.25},
        expected_type=PulseOscillator,
    ),
    DiscriminationCase(
        name="white_noise",
        adapter=OSCILLATOR_ADAPTER,
        payload={"kind": "white_noise"},
        expected_type=WhiteNoiseOscillator,
    ),
    DiscriminationCase(
        name="walk_noise",
        adapter=OSCILLATOR_ADAPTER,
        payload={"kind": "walk_noise"},
        expected_type=WalkNoiseOscillator,
    ),
    DiscriminationCase(
        name="exponential_decay",
        adapter=ENVELOPE_ADAPTER,
        payload={"kind": "exponential_decay", "time_constant_seconds": 0.15},
        expected_type=ExponentialDecayEnvelope,
    ),
    DiscriminationCase(
        name="linear_attack",
        adapter=ENVELOPE_ADAPTER,
        payload={"kind": "linear_attack", "attack_seconds": 0.005},
        expected_type=LinearAttackEnvelope,
    ),
    DiscriminationCase(
        name="linear_ramp",
        adapter=ENVELOPE_ADAPTER,
        payload={"kind": "linear_ramp"},
        expected_type=LinearRampEnvelope,
    ),
)


class TestUnionDiscrimination:
    @pytest.mark.parametrize(
        "case",
        DISCRIMINATION_CASES,
        ids=lambda case: case.name,
    )
    def test_kind_selects_the_member_class(
        self,
        case: DiscriminationCase,
    ) -> None:
        assert isinstance(
            case.adapter.validate_python(case.payload),
            case.expected_type,
        )

    @pytest.mark.parametrize(
        "adapter",
        (OSCILLATOR_ADAPTER, ENVELOPE_ADAPTER),
        ids=("oscillators", "envelopes"),
    )
    def test_unknown_kind_is_rejected(self, adapter: TypeAdapter[Any]) -> None:
        with pytest.raises(ValidationError):
            adapter.validate_python({"kind": "unknown"})

    def test_extra_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OSCILLATOR_ADAPTER.validate_python(
                {
                    "kind": "sine",
                    "frequency": 440.0,
                    "volume": 1.0,
                }
            )
