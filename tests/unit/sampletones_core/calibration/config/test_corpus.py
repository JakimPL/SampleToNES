from dataclasses import dataclass
from typing import Any, Dict, Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.calibration.config.corpus import CorpusConfig

VALID_TRANSIENT: Final[Dict[str, Any]] = {
    "snare_decay_seconds": 0.15,
    "kick_decay_seconds": 0.25,
    "kick_sweep_frequencies": (150.0, 50.0),
    "attack_seconds": 0.005,
    "attack_tone_decay_seconds": 0.3,
}

VALID_FIELDS: Final[Dict[str, Any]] = {
    "seed": 1,
    "item_seconds": 1.5,
    "amplitude": 0.5,
    "reference_frequency": 440.0,
    "tone": {"frequencies": (55.0, 440.0)},
    "timbre": {"duty_cycles": (0.125, 0.5), "frequency": 220.0},
    "noise": {"white_level": 0.5},
    "mix": {"noise_levels": (0.05, 0.15)},
    "transient": VALID_TRANSIENT,
}


@dataclass(frozen=True)
class InvalidFieldCase:
    name: str
    field: str
    value: Any


INVALID_FIELD_CASES: Final[Tuple[InvalidFieldCase, ...]] = (
    InvalidFieldCase(name="negative_seed", field="seed", value=-1),
    InvalidFieldCase(name="zero_item_seconds", field="item_seconds", value=0.0),
    InvalidFieldCase(name="zero_amplitude", field="amplitude", value=0.0),
    InvalidFieldCase(name="amplitude_above_full_scale", field="amplitude", value=1.5),
    InvalidFieldCase(name="zero_reference_frequency", field="reference_frequency", value=0.0),
    InvalidFieldCase(name="empty_tone_frequencies", field="tone", value={"frequencies": ()}),
    InvalidFieldCase(
        name="nonpositive_tone_frequency",
        field="tone",
        value={"frequencies": (440.0, 0.0)},
    ),
    InvalidFieldCase(
        name="empty_duty_cycles",
        field="timbre",
        value={"duty_cycles": (), "frequency": 220.0},
    ),
    InvalidFieldCase(
        name="duty_cycle_at_full_width",
        field="timbre",
        value={"duty_cycles": (1.0,), "frequency": 220.0},
    ),
    InvalidFieldCase(
        name="zero_timbre_frequency",
        field="timbre",
        value={"duty_cycles": (0.5,), "frequency": 0.0},
    ),
    InvalidFieldCase(name="zero_white_noise_level", field="noise", value={"white_level": 0.0}),
    InvalidFieldCase(name="empty_mix_noise_levels", field="mix", value={"noise_levels": ()}),
    InvalidFieldCase(
        name="zero_snare_decay",
        field="transient",
        value={**VALID_TRANSIENT, "snare_decay_seconds": 0.0},
    ),
    InvalidFieldCase(
        name="zero_attack",
        field="transient",
        value={**VALID_TRANSIENT, "attack_seconds": 0.0},
    ),
)


class TestCorpusConfig:
    def test_packaged_configuration_loads(self) -> None:
        config = CorpusConfig.load()
        assert isinstance(config, CorpusConfig)

    @pytest.mark.parametrize("case", INVALID_FIELD_CASES, ids=lambda case: case.name)
    def test_out_of_bounds_field_is_rejected(self, case: InvalidFieldCase) -> None:
        fields = {**VALID_FIELDS, case.field: case.value}
        with pytest.raises(ValidationError):
            CorpusConfig.model_validate(fields)

    @pytest.mark.parametrize("field", sorted(VALID_FIELDS))
    def test_missing_field_is_rejected(self, field: str) -> None:
        fields = {key: value for key, value in VALID_FIELDS.items() if key != field}
        with pytest.raises(ValidationError):
            CorpusConfig.model_validate(fields)
