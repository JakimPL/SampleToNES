from dataclasses import dataclass
from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_core.calibration.config.corpus import CorpusConfig
from tests.suite.case import BaseRegularTestCase

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


class TestCorpusConfig:
    @dataclass(frozen=True, kw_only=True)
    class InvalidFieldCase(BaseRegularTestCase):
        field: str
        value: Any

    test_cases = (
        InvalidFieldCase(
            field="seed",
            value=-1,
            label="negative_seed",
        ),
        InvalidFieldCase(
            field="item_seconds",
            value=0.0,
            label="zero_item_seconds",
        ),
        InvalidFieldCase(
            field="amplitude",
            value=0.0,
            label="zero_amplitude",
        ),
        InvalidFieldCase(
            field="amplitude",
            value=1.5,
            label="amplitude_above_full_scale",
        ),
        InvalidFieldCase(
            field="reference_frequency",
            value=0.0,
            label="zero_reference_frequency",
        ),
        InvalidFieldCase(
            field="tone",
            value={"frequencies": ()},
            label="empty_tone_frequencies",
        ),
        InvalidFieldCase(
            field="tone",
            value={"frequencies": (440.0, 0.0)},
            label="nonpositive_tone_frequency",
        ),
        InvalidFieldCase(
            field="timbre",
            value={"duty_cycles": (), "frequency": 220.0},
            label="empty_duty_cycles",
        ),
        InvalidFieldCase(
            field="timbre",
            value={"duty_cycles": (1.0,), "frequency": 220.0},
            label="duty_cycle_at_full_width",
        ),
        InvalidFieldCase(
            field="timbre",
            value={"duty_cycles": (0.5,), "frequency": 0.0},
            label="zero_timbre_frequency",
        ),
        InvalidFieldCase(
            field="noise",
            value={"white_level": 0.0},
            label="zero_white_noise_level",
        ),
        InvalidFieldCase(
            field="mix",
            value={"noise_levels": ()},
            label="empty_mix_noise_levels",
        ),
        InvalidFieldCase(
            field="transient",
            value={**VALID_TRANSIENT, "snare_decay_seconds": 0.0},
            label="zero_snare_decay",
        ),
        InvalidFieldCase(
            field="transient",
            value={**VALID_TRANSIENT, "attack_seconds": 0.0},
            label="zero_attack",
        ),
    )

    def test_packaged_configuration_loads(self) -> None:
        config = CorpusConfig.load()
        assert isinstance(config, CorpusConfig)

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_out_of_bounds_field_is_rejected(self, case: InvalidFieldCase) -> None:
        fields = {**VALID_FIELDS, case.field: case.value}
        with pytest.raises(ValidationError):
            CorpusConfig.model_validate(fields)

    @pytest.mark.parametrize("field", sorted(VALID_FIELDS))
    def test_missing_field_is_rejected(self, field: str) -> None:
        fields = {key: value for key, value in VALID_FIELDS.items() if key != field}
        with pytest.raises(ValidationError):
            CorpusConfig.model_validate(fields)
