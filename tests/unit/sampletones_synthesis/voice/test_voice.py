from typing import Any, Dict, Final

import numpy as np
import pytest
from pydantic import ValidationError

from sampletones_synthesis.oscillators.sine import SineOscillator
from sampletones_synthesis.voice.layer import Layer
from sampletones_synthesis.voice.voice import Voice

DURATION_SECONDS: Final[float] = 0.5
LOW_FREQUENCY: Final[float] = 220.0
HIGH_FREQUENCY: Final[float] = 880.0

VOICE_MAPPING: Final[Dict[str, Any]] = {
    "duration_seconds": DURATION_SECONDS,
    "layers": [
        {
            "oscillator": {"kind": "geometric_sweep", "frequency_start": 67, "frequency_end": 29},
            "envelopes": [{"kind": "exponential_decay", "time_constant_seconds": 0.066}],
            "gain": 1.0,
        },
        {
            "oscillator": {"kind": "white_noise"},
            "envelopes": [],
            "gain": 0.15,
        },
    ],
    "filters": [{"kind": "butterworth_highpass", "cutoff_hz": 5000.0, "order": 4}],
}


def _tone_layer(frequency: float, gain: float) -> Layer:
    return Layer(oscillator=SineOscillator(kind="sine", frequency=frequency), envelopes=(), gain=gain)


class TestVoice:
    def test_layers_sum(self, sample_rate: int, generator: np.random.Generator) -> None:
        low = _tone_layer(LOW_FREQUENCY, gain=1.0)
        high = _tone_layer(HIGH_FREQUENCY, gain=0.25)
        voice = Voice(duration_seconds=DURATION_SECONDS, layers=(low, high), filters=())

        audio = voice.render(sample_rate=sample_rate, generator=generator)
        time = np.arange(round(DURATION_SECONDS * sample_rate), dtype=np.float64) / sample_rate
        expected = low.render(time, generator=generator) + high.render(time, generator=generator)
        assert np.allclose(audio, expected)

    def test_output_is_float64_of_the_configured_length(
        self,
        sample_rate: int,
        generator: np.random.Generator,
    ) -> None:
        voice = Voice(duration_seconds=DURATION_SECONDS, layers=(_tone_layer(LOW_FREQUENCY, 1.0),), filters=())
        audio = voice.render(sample_rate=sample_rate, generator=generator)
        assert audio.dtype == np.float64
        assert audio.shape == (round(DURATION_SECONDS * sample_rate),)

    def test_seeded_render_is_deterministic(self, sample_rate: int) -> None:
        voice = Voice.model_validate(VOICE_MAPPING)
        first = voice.render(sample_rate=sample_rate, generator=np.random.default_rng(7))
        second = voice.render(sample_rate=sample_rate, generator=np.random.default_rng(7))
        assert np.array_equal(first, second)

    def test_mapping_round_trip_preserves_the_voice(self) -> None:
        voice = Voice.model_validate(VOICE_MAPPING)
        assert Voice.model_validate(voice.model_dump()) == voice

    def test_voice_without_layers_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Voice(duration_seconds=DURATION_SECONDS, layers=(), filters=())

    def test_duration_below_two_samples_is_rejected(self, generator: np.random.Generator) -> None:
        voice = Voice(duration_seconds=1e-6, layers=(_tone_layer(LOW_FREQUENCY, 1.0),), filters=())
        with pytest.raises(ValueError):
            voice.render(sample_rate=22050, generator=generator)
