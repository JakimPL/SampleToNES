import math
from typing import Final, List, Optional

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.fft.instantaneous import FundamentalReading, InstantaneousPitch
from sampletones_core.generators.implementation.triangle import TriangleGenerator
from sampletones_core.instructions import TriangleInstruction

SAMPLE_RATE: Final[int] = 44100
HOP: Final[int] = 735
SECONDS: Final[float] = 0.5
A4_FREQUENCY: Final[float] = 440.0
CENTS_PER_OCTAVE: Final[float] = 1200.0
CENT_TOLERANCE: Final[float] = 1.0
PITCHED_CONFIDENCE: Final[float] = 0.2
UNPITCHED_CONFIDENCE: Final[float] = 0.1
NOISE_SEED: Final[int] = 4
TRIANGLE_FRAMES: Final[int] = 120
SETTLED_FRAMES: Final[int] = 30
TRIANGLE_CENT_TOLERANCE: Final[float] = 20.0
BASS_SECONDS: Final[float] = 2.0
BASS_LEVEL: Final[float] = 0.3
LOW_BASS_FREQUENCY: Final[float] = 36.71
SHARE_TOLERANCE: Final[float] = 0.1
HIGH_FREQUENCIES: Final[tuple[float, ...]] = (1760.0, 3520.0)
FAR_INSIDE_CENTS: Final[tuple[float, ...]] = (-40.0, 40.0)
PULSE_A6_DIVIDER_FREQUENCY: Final[float] = 1747.8
PAST_HALF_A_SEMITONE_CENTS: Final[float] = 52.0
VIBRATO_FREQUENCY: Final[float] = 1760.0
VIBRATO_DEPTH_CENTS: Final[float] = 35.0
VIBRATO_RATE: Final[float] = 5.5
VIBRATO_SECONDS: Final[float] = 2.0
VIBRATO_CENT_TOLERANCE: Final[float] = 10.0
BASS_FREQUENCY: Final[float] = 65.41
BESIDE_FIFTH_HARMONIC: Final[float] = 349.23
ON_FOURTH_HARMONIC: Final[float] = 4 * BASS_FREQUENCY


def _harmonic(frequency: float, seed: int = 0, seconds: float = SECONDS) -> np.ndarray:
    """A steady tone with a full harmonic series, which is what a pitched frame looks like."""
    generator = np.random.default_rng(seed)
    count = int(SAMPLE_RATE * seconds)
    time = np.arange(count) / SAMPLE_RATE
    audio = np.zeros(count)
    for harmonic in range(1, 20):
        if frequency * harmonic > SAMPLE_RATE / 2:
            break

        audio += np.sin(2 * np.pi * frequency * harmonic * time + generator.uniform(0, 2 * np.pi)) / harmonic

    scaled: np.ndarray = (audio / np.abs(audio).max() * 0.3).astype(np.float32)
    return scaled


def _bass(frequency: float, level: float) -> np.ndarray:
    """A pure low tone lasting long enough for the lowest bins to settle."""
    time = np.arange(int(SAMPLE_RATE * BASS_SECONDS)) / SAMPLE_RATE
    audio: np.ndarray = (level * np.sin(2 * np.pi * frequency * time)).astype(np.float32)
    return audio


def _triangle(frequency: float) -> np.ndarray:
    """A triangle wave, whose odd harmonics leave every other harmonic bin to the voices around it."""
    phase = frequency * np.arange(int(SAMPLE_RATE * BASS_SECONDS)) / SAMPLE_RATE
    audio: np.ndarray = (BASS_LEVEL * (1.0 - 4.0 * np.abs((phase % 1.0) - 0.5))).astype(np.float32)
    return audio


def _bass_cents_under(melody_frequency: float) -> float:
    """Where a triangle bass is read, in cents from where it stands, under a melody note."""
    melody = _harmonic(melody_frequency, seconds=BASS_SECONDS)
    readings = _readings(_triangle(BASS_FREQUENCY) + melody, BASS_FREQUENCY)
    return _median_cents(readings, BASS_FREQUENCY)


def _melody_share(bass: np.ndarray) -> float:
    """The median confidence of a melody note read over a bass."""
    melody = _harmonic(A4_FREQUENCY, seconds=BASS_SECONDS)
    readings = _readings(melody + bass, A4_FREQUENCY)
    return float(np.median([reading.confidence for reading in readings]))


def _readings(audio: np.ndarray, reference: float) -> List[FundamentalReading]:
    reader = InstantaneousPitch(audio, SAMPLE_RATE, HOP)
    read: List[Optional[FundamentalReading]] = [reader.at(frame, reference) for frame in range(reader.columns)]
    return [reading for reading in read if reading is not None]


def _median_cents(readings: List[FundamentalReading], reference: float) -> float:
    return CENTS_PER_OCTAVE * math.log2(float(np.median([reading.frequency for reading in readings])) / reference)


class TestReadingAFundamental:
    @pytest.mark.parametrize("cents", (-45.0, -18.0, 0.0, 25.0, 40.0), ids=lambda cents: f"{cents:+.0f}c")
    def test_a_tone_between_two_notes_is_read_where_it_stands(self, cents: float) -> None:
        """The bins are a semitone apart, and the phase places the tone far inside one of them."""
        truth = A4_FREQUENCY * 2 ** (cents / CENTS_PER_OCTAVE)

        readings = _readings(_harmonic(truth), A4_FREQUENCY)

        assert readings
        assert abs(_median_cents(readings, A4_FREQUENCY) - cents) < CENT_TOLERANCE

    def test_a_reading_is_taken_for_every_frame_of_the_recording(self) -> None:
        reader = InstantaneousPitch(_harmonic(A4_FREQUENCY), SAMPLE_RATE, HOP)

        assert all(reader.at(frame, A4_FREQUENCY) is not None for frame in range(reader.columns))

    def test_a_frame_outside_the_recording_is_read_as_nothing(self) -> None:
        reader = InstantaneousPitch(_harmonic(A4_FREQUENCY), SAMPLE_RATE, HOP)

        assert reader.at(-1, A4_FREQUENCY) is None
        assert reader.at(reader.columns, A4_FREQUENCY) is None

    def test_a_reference_the_transform_never_reaches_is_read_as_nothing(self) -> None:
        reader = InstantaneousPitch(_harmonic(A4_FREQUENCY), SAMPLE_RATE, HOP)

        assert reader.at(1, SAMPLE_RATE) is None


def _vibrato() -> tuple[np.ndarray, np.ndarray]:
    """A square-wave vibrato and the frequency it sounds at between each pair of columns."""
    time = np.arange(int(SAMPLE_RATE * VIBRATO_SECONDS)) / SAMPLE_RATE
    depth = VIBRATO_DEPTH_CENTS / CENTS_PER_OCTAVE
    frequency = VIBRATO_FREQUENCY * 2 ** (depth * np.sin(2 * np.pi * VIBRATO_RATE * time))
    phase = np.cumsum(frequency) / SAMPLE_RATE
    audio = (0.3 * np.where(phase % 1.0 < 0.5, 1.0, -1.0)).astype(np.float32)
    frames = len(time) // HOP
    sounding = frequency[: frames * HOP].reshape(frames, HOP).mean(axis=1)
    return audio, sounding


class TestTheTopOfTheRange:
    """A reading repeats every ``sample_rate / hop`` hertz, a span narrower than a note's room from about
    1 kHz up. A tone far inside its room there is read on its own side."""

    @pytest.mark.parametrize("frequency", HIGH_FREQUENCIES, ids=lambda frequency: f"{frequency:g} Hz")
    @pytest.mark.parametrize("cents", FAR_INSIDE_CENTS, ids=lambda cents: f"{cents:+.0f}c")
    def test_a_tone_far_inside_its_room_is_read_where_it_stands(self, frequency: float, cents: float) -> None:
        truth = frequency * 2 ** (cents / CENTS_PER_OCTAVE)

        readings = _readings(_harmonic(truth), frequency)

        assert abs(_median_cents(readings, frequency) - cents) < CENT_TOLERANCE

    def test_a_tone_nearest_a_note_whose_divider_stands_flat_is_read_where_it_stands(self) -> None:
        """The pulse's A6 divider sounds 12 cents flat, so a tone 40 cents sharp of A6 stands 52 cents
        from the note the decoder names, which is still the nearest one."""
        cents = PAST_HALF_A_SEMITONE_CENTS
        truth = PULSE_A6_DIVIDER_FREQUENCY * 2 ** (cents / CENTS_PER_OCTAVE)

        readings = _readings(_harmonic(truth), PULSE_A6_DIVIDER_FREQUENCY)

        assert abs(_median_cents(readings, PULSE_A6_DIVIDER_FREQUENCY) - cents) < CENT_TOLERANCE

    def test_a_vibrato_is_read_on_its_own_side_at_every_frame(self) -> None:
        audio, sounding = _vibrato()
        reader = InstantaneousPitch(audio, SAMPLE_RATE, HOP)

        errors = [
            abs(CENTS_PER_OCTAVE * math.log2(reading.frequency / sounding[frame]))
            for frame in range(SETTLED_FRAMES, len(sounding) - SETTLED_FRAMES)
            if (reading := reader.at(frame, VIBRATO_FREQUENCY)) is not None
        ]

        assert errors
        assert max(errors) < VIBRATO_CENT_TOLERANCE


class TestTheTrianglesLowestOctave:
    """The triangle sounds an octave below the pulse at the same divider, so its lowest notes stand
    below every pulse note. The transform reaches them, and their fundamental is read where the
    channel sounds it on every frame, the frames a recording's edges cut short aside."""

    @pytest.mark.parametrize("pitch", (33, 37, 41, 44), ids=lambda pitch: f"pitch {pitch}")
    def test_every_settled_frame_is_read_where_the_channel_sounds(self, pitch: int) -> None:
        generator = TriangleGenerator(Config())
        instruction = TriangleInstruction(on=True, pitch=pitch)
        audio = np.concatenate([generator(instruction, save=True) for _ in range(TRIANGLE_FRAMES)])
        sounding = generator.sounds_at(pitch, 0)
        reader = InstantaneousPitch(audio, SAMPLE_RATE, HOP)

        readings = [reader.at(frame, sounding) for frame in range(SETTLED_FRAMES, TRIANGLE_FRAMES - SETTLED_FRAMES)]

        assert all(reading is not None for reading in readings)
        assert all(
            abs(CENTS_PER_OCTAVE * math.log2(reading.frequency / sounding)) < TRIANGLE_CENT_TOLERANCE
            for reading in readings
            if reading is not None
        )


class TestAnotherVoiceBesideTheHarmonics:
    """A harmonic reads where its partial stands, so a partial another voice sounds a bin away from one
    of a note's harmonics would pull the note's reading toward it."""

    def test_a_voice_beside_a_harmonic_leaves_the_reading_in_place(self) -> None:
        assert abs(_bass_cents_under(BESIDE_FIFTH_HARMONIC)) < CENT_TOLERANCE

    def test_a_voice_on_a_harmonic_agrees_with_the_note(self) -> None:
        """The triangle has no fourth harmonic, so the melody's fundamental fills that bin alone, at the
        frequency the note puts it."""
        assert abs(_bass_cents_under(ON_FOURTH_HARMONIC)) < CENT_TOLERANCE


class TestHowMuchOfAFrameStandsBehindItsReading:
    def test_a_pitched_frame_reads_with_confidence(self) -> None:
        readings = _readings(_harmonic(A4_FREQUENCY), A4_FREQUENCY)

        assert float(np.median([reading.confidence for reading in readings])) > PITCHED_CONFIDENCE

    def test_noise_reads_with_none(self) -> None:
        """Noise spreads its energy everywhere, so the harmonics of any note hold little of it."""
        count = int(SAMPLE_RATE * SECONDS)
        noise = np.random.default_rng(NOISE_SEED).normal(0.0, 0.3, count).astype(np.float32)

        readings = _readings(noise, A4_FREQUENCY)

        assert float(np.median([reading.confidence for reading in readings])) < UNPITCHED_CONFIDENCE

    def test_a_tone_sharing_the_frame_lowers_the_share_without_moving_the_reading(self) -> None:
        alone = _harmonic(A4_FREQUENCY)
        crowded = alone + _harmonic(A4_FREQUENCY * 1.5, seed=7)

        readings = _readings(crowded, A4_FREQUENCY)

        assert abs(_median_cents(readings, A4_FREQUENCY)) < CENT_TOLERANCE
        assert float(np.median([reading.confidence for reading in readings])) < float(
            np.median([reading.confidence for reading in _readings(alone, A4_FREQUENCY)])
        )

    def test_a_bass_takes_the_same_share_in_every_register(self) -> None:
        """A bass an octave lower is no louder, so a melody over it keeps the share it holds."""
        low = _melody_share(_bass(LOW_BASS_FREQUENCY, BASS_LEVEL))
        higher = _melody_share(_bass(2 * LOW_BASS_FREQUENCY, BASS_LEVEL))

        assert abs(low - higher) < SHARE_TOLERANCE * higher

    def test_a_louder_bass_takes_a_larger_share(self) -> None:
        quiet = _melody_share(_bass(LOW_BASS_FREQUENCY, BASS_LEVEL))
        loud = _melody_share(_bass(LOW_BASS_FREQUENCY, 2 * BASS_LEVEL))

        assert loud < quiet
