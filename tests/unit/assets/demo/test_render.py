from typing import Final

import numpy as np

from assets.demo.render import leveled, pitched, render_stem, sounding
from assets.demo.specification import Note, Stem
from sampletones_tools.synthesis.oscillators.pulse import PulseOscillator
from sampletones_tools.synthesis.oscillators.white_noise import WhiteNoiseOscillator
from sampletones_tools.synthesis.voice.layer import Layer
from sampletones_tools.synthesis.voice.voice import Voice

SAMPLE_RATE: Final[int] = 8000
TEMPO: Final[float] = 120.0
SECONDS_PER_BEAT: Final[float] = 0.5
BEATS: Final[float] = 2.0
SEED: Final[int] = 7
PITCH: Final[int] = 60
AMPLITUDE: Final[float] = 0.5

PULSE: Final[Voice] = Voice(
    duration_seconds=0.25,
    layers=(Layer(oscillator=PulseOscillator(kind="pulse", frequency=45, duty_cycle=0.5), envelopes=(), gain=1.0),),
    filters=(),
)
NOISE: Final[Voice] = Voice(
    duration_seconds=0.25,
    layers=(Layer(oscillator=WhiteNoiseOscillator(kind="white_noise"), envelopes=(), gain=1.0),),
    filters=(),
)


def rendered(stem: Stem, seed: int) -> np.ndarray:
    return render_stem(
        stem,
        {"pulse": PULSE, "noise": NOISE},
        tempo=TEMPO,
        beats=BEATS,
        sample_rate=SAMPLE_RATE,
        generator=np.random.default_rng(seed),
    )


class TestSounding:
    def test_a_pitched_note_moves_a_pitched_oscillator(self) -> None:
        voice = sounding(PULSE, Note(voice="pulse", start=0.0, length=1.0, pitch=PITCH), SECONDS_PER_BEAT)

        assert isinstance(voice.layers[0].oscillator, PulseOscillator)
        assert voice.layers[0].oscillator.frequency == PITCH

    def test_a_pitched_note_leaves_an_unpitched_oscillator_as_it_is(self) -> None:
        oscillator = NOISE.layers[0].oscillator

        assert pitched(oscillator, PITCH) == oscillator

    def test_a_note_with_a_length_lasts_that_many_beats(self) -> None:
        voice = sounding(PULSE, Note(voice="pulse", start=0.0, length=1.5, pitch=None), SECONDS_PER_BEAT)

        assert voice.duration_seconds == 1.5 * SECONDS_PER_BEAT

    def test_a_note_without_a_length_lasts_the_voice_s_own(self) -> None:
        voice = sounding(PULSE, Note(voice="pulse", start=0.0, length=None, pitch=None), SECONDS_PER_BEAT)

        assert voice.duration_seconds == PULSE.duration_seconds


class TestRenderStem:
    def test_the_stem_lasts_the_piece(self) -> None:
        stem = Stem(name="One", notes=(Note(voice="pulse", start=0.0, length=1.0, pitch=None),))

        assert rendered(stem, SEED).shape[0] == round(BEATS * SECONDS_PER_BEAT * SAMPLE_RATE)

    def test_a_note_sounds_from_its_beat_and_silence_stands_before_it(self) -> None:
        stem = Stem(name="Late", notes=(Note(voice="pulse", start=1.0, length=0.5, pitch=None),))
        audio = rendered(stem, SEED)
        onset = round(1.0 * SECONDS_PER_BEAT * SAMPLE_RATE)

        assert not audio[:onset].any()
        assert audio[onset:].any()

    def test_a_note_running_past_the_piece_is_cut_at_its_end(self) -> None:
        stem = Stem(name="Long", notes=(Note(voice="pulse", start=1.5, length=4.0, pitch=None),))

        assert rendered(stem, SEED).shape[0] == round(BEATS * SECONDS_PER_BEAT * SAMPLE_RATE)

    def test_the_same_seed_renders_the_same_noise(self) -> None:
        stem = Stem(name="Noise", notes=(Note(voice="noise", start=0.0, length=None, pitch=None),))

        assert np.array_equal(rendered(stem, SEED), rendered(stem, SEED))
        assert not np.array_equal(rendered(stem, SEED), rendered(stem, SEED + 1))


class TestLeveled:
    def test_the_peak_reaches_the_amplitude(self) -> None:
        audio = np.array([0.1, -0.2, 0.05])

        assert float(np.abs(leveled(audio, AMPLITUDE)).max()) == AMPLITUDE

    def test_silence_stays_silent(self) -> None:
        assert not leveled(np.zeros(4), AMPLITUDE).any()

    def test_the_result_is_ready_to_write(self) -> None:
        assert leveled(np.array([0.3, -0.3]), AMPLITUDE).dtype == np.float32
