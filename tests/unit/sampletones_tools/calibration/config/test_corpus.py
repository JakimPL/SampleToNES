from dataclasses import dataclass
from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_tools.calibration.config.corpus import CorpusConfig
from tests.suite.case import BaseRegularTestCase

VALID_TRANSIENT: Final[Dict[str, Any]] = {
    "snare_decay_seconds": 0.15,
    "kick_decay_seconds": 0.25,
    "kick_sweep_frequencies": (150.0, 50.0),
    "attack_seconds": 0.005,
    "attack_tone_decay_seconds": 0.3,
}

VALID_POLYPHONY: Final[Dict[str, Any]] = {
    "chord_frequencies": (220.0, 277.18),
    "melody_frequencies": (440.0, 523.25),
    "note_seconds": 0.25,
    "note_decay_seconds": 0.4,
    "snare_period_seconds": 0.5,
    "snare_delay_seconds": 0.25,
    "snare_decay_seconds": 0.04,
    "snare_level": 0.35,
}

VALID_MIX: Final[Dict[str, Any]] = {
    "noise_levels": (0.05, 0.15),
    "bass_frequency": 55.0,
    "hat_period_seconds": 0.25,
    "hat_decay_seconds": 0.008,
    "hat_level": 0.4,
}

VALID_DYNAMICS: Final[Dict[str, Any]] = {
    "burst_seconds": 0.2,
    "hiss_level": 0.09,
}

VALID_FIELDS: Final[Dict[str, Any]] = {
    "seed": 1,
    "item_seconds": 1.5,
    "amplitude": 0.5,
    "reference_frequency": 440.0,
    "tone": {"frequencies": (55.0, 440.0)},
    "timbre": {"duty_cycles": (0.125, 0.5), "frequency": 220.0},
    "noise": {"white_level": 0.5},
    "mix": VALID_MIX,
    "transient": VALID_TRANSIENT,
    "polyphony": VALID_POLYPHONY,
    "dynamics": VALID_DYNAMICS,
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
            value={**VALID_MIX, "noise_levels": ()},
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
        InvalidFieldCase(
            field="polyphony",
            value={**VALID_POLYPHONY, "chord_frequencies": (220.0,)},
            label="single_note_chord",
        ),
        InvalidFieldCase(
            field="polyphony",
            value={**VALID_POLYPHONY, "note_seconds": 0.0},
            label="zero_note_seconds",
        ),
        InvalidFieldCase(
            field="dynamics",
            value={**VALID_DYNAMICS, "hiss_level": 1.0},
            label="hiss_as_loud_as_the_burst",
        ),
        InvalidFieldCase(
            field="mix",
            value={**VALID_MIX, "hat_period_seconds": 0.0},
            label="zero_hat_period",
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
