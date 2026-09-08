import math
from pathlib import Path
from typing import Any, Dict, Final, List

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.configs.generation import GenerationConfig
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    FeatureKey,
)
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.fft.instantaneous import InstantaneousPitch
from sampletones_core.generators import PulseGenerator, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryFragment,
)
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstructor.refinement import refiner
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig

PITCH: Final[int] = 60
NEIGHBORHOOD: Final[range] = range(PITCH - 2, PITCH + 3)
DUTY_CYCLE: Final[int] = 2
SECONDS: Final[float] = 1.0
CENTS_PER_OCTAVE: Final[float] = 1200.0
DETUNE_CENTS: Final[float] = 30.0
CENTS_TOLERANCE: Final[float] = 8.0
NOISE_SEED: Final[int] = 11
EDGE_FRAMES: Final[int] = 1
PULSE_ONLY: Final[List[ChannelName]] = [ChannelName.PULSE1]
BENDING: Final[List[ChannelName]] = [ChannelName.PULSE1]
UNBENT: Final[List[ChannelName]] = []


def _config() -> Config:
    return Config()


def _library(config: Config) -> InstructionLibrary:
    """A catalog of the notes around the target, at every volume the pulse channel offers.

    Nothing in it is bent: the catalog is the equal-tempered grid the matching chooses from, and
    the bend is what the refinement adds on top of that choice.
    """
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    generator = get_generators_by_channels(config, PULSE_ONLY)[ChannelName.PULSE1]

    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for instruction in generator.get_possible_instructions():
        if instruction.on and instruction.pitch not in NEIGHBORHOOD:
            continue

        if instruction.on and instruction.duty_cycle != DUTY_CYCLE:
            continue

        data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def _square_path(path: Path, config: Config, cents: float, seconds: float = SECONDS) -> Path:
    """A steady square tone standing ``cents`` off the note the catalog holds."""
    sample_rate = config.library.sample_rate
    generator = PulseGenerator(config, ChannelName.PULSE1)
    frequency = generator.sounds_at(PITCH, 0) * 2 ** (cents / CENTS_PER_OCTAVE)

    count = int(sample_rate * seconds)
    phase = (np.arange(count) * frequency / sample_rate) % 1.0
    audio = np.where(phase < 0.5, 0.4, -0.4)

    write_wave(path, sample_rate, audio)
    return path


def _noise_path(path: Path, config: Config) -> Path:
    sample_rate = config.library.sample_rate
    count = int(sample_rate * SECONDS)
    audio = np.random.default_rng(NOISE_SEED).normal(0.0, 0.3, count)

    write_wave(path, sample_rate, audio)
    return path


def _reconstruct(config: Config, audio_path: Path, bends: List[ChannelName]) -> Reconstruction:
    """The conversion of one recording by a stem carrying the channels ``bends`` names."""
    reconstructor = Reconstructor(config, frozenset(PULSE_ONLY), library=_library(config))
    reconstruction = reconstructor.reconstruct(
        [audio_path],
        StemsConfig.single_entry(PULSE_ONLY, bends),
    )
    assert reconstruction is not None
    return reconstruction


def _sounding(reconstruction: Reconstruction) -> List[PulseInstruction]:
    return [
        instruction
        for instruction in reconstruction.instructions[ChannelName.PULSE1]
        if isinstance(instruction, PulseInstruction) and instruction.on
    ]


def _cents_off(config: Config, instruction: PulseInstruction) -> float:
    """How far the frame sounds from the note it names, in cents."""
    generator = PulseGenerator(config, ChannelName.PULSE1)
    bent = generator.sounds_at(instruction.pitch, instruction.timer_offset)
    named = generator.sounds_at(instruction.pitch, 0)
    return CENTS_PER_OCTAVE * math.log2(bent / named)


@pytest.fixture(scope="module")
def config() -> Config:
    return _config()


class TestAConversionLandsOnTheNoteTheSourceSounds:
    """A source recorded off the equal-tempered grid comes back bent onto its own tuning.

    The catalog holds whole semitones, so the matching can only reach the nearest note; the
    hardware's divider grid is finer than that, and the refinement is what spends the difference.
    """

    def test_a_detuned_tone_comes_back_bent_toward_its_own_pitch(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        reconstruction = _reconstruct(config, _square_path(tmp_path / "sharp.wav", config, DETUNE_CENTS), BENDING)

        sounding = _sounding(reconstruction)
        assert sounding
        measured = float(np.median([_cents_off(config, frame) for frame in sounding]))

        assert abs(measured - DETUNE_CENTS) < CENTS_TOLERANCE

    def test_a_tone_already_on_the_grid_is_left_where_it_is(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        reconstruction = _reconstruct(config, _square_path(tmp_path / "flat.wav", config, 0.0), BENDING)

        sounding = _sounding(reconstruction)
        assert sounding
        measured = float(np.median([_cents_off(config, frame) for frame in sounding]))

        assert abs(measured) < CENTS_TOLERANCE

    def test_the_bend_holds_rather_than_wandering(self, config: Config, tmp_path: Path) -> None:
        """A steady tone is one tuning, so the stream settles on one bend and keeps it.

        The opening and closing frames are read across the edge of the recording, where the
        constant-Q window reaches past what was recorded, so the interior is what a held tuning
        shows in.
        """
        reconstruction = _reconstruct(config, _square_path(tmp_path / "steady.wav", config, DETUNE_CENTS), BENDING)

        bends = [frame.timer_offset for frame in _sounding(reconstruction)]
        interior = bends[EDGE_FRAMES:-EDGE_FRAMES]

        assert interior
        assert len(set(interior)) == 1


class TestWhatTheRefinementLeavesAlone:
    def test_a_stem_carrying_no_channel_bends_nothing(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        reconstruction = _reconstruct(config, _square_path(tmp_path / "unrefined.wav", config, DETUNE_CENTS), UNBENT)

        assert all(not frame.bent for frame in _sounding(reconstruction))

    def test_a_stem_carrying_no_channel_records_the_bend_as_the_channels(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        """Nothing bent means nothing chosen, so both dimensions stay the channel's own."""
        reconstruction = _reconstruct(config, _square_path(tmp_path / "held.wav", config, DETUNE_CENTS), UNBENT)
        held = reconstruction.held_features[ChannelName.PULSE1]

        assert FeatureKey.PITCH in held
        assert FeatureKey.HI_PITCH in held

    def test_a_source_with_no_pitch_to_read_is_left_unbent(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        """Noise states no fundamental, so no frame of it earns a bend."""
        reconstruction = _reconstruct(config, _noise_path(tmp_path / "noise.wav", config), BENDING)

        assert all(not frame.bent for frame in _sounding(reconstruction))


class TestWhatTheRefinementReads:
    """The refinement reads a recording rather than searching it.

    What it adds to a conversion is one transform per stem and a walk over the frames: no
    candidate is enumerated and nothing is rescored. Counting the readings holds that where a
    clock cannot — what one transform costs is the machine's own, and a CUDA build and a CPU
    build disagree about it by two orders of magnitude, so a reading per stem is the claim worth
    pinning.
    """

    @staticmethod
    def _counted(monkeypatch: pytest.MonkeyPatch) -> List[int]:
        """The frames of each recording the refinement reads, in the order it reads them."""
        readings: List[int] = []

        def counting(recording: np.ndarray, sample_rate: int, hop_length: int) -> InstantaneousPitch:
            readings.append(len(recording))
            return InstantaneousPitch(recording, sample_rate, hop_length)

        monkeypatch.setattr(refiner, "InstantaneousPitch", counting)
        return readings

    def test_a_refined_conversion_reads_each_recording_once(
        self,
        config: Config,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        readings = self._counted(monkeypatch)
        _reconstruct(config, _square_path(tmp_path / "read.wav", config, DETUNE_CENTS), BENDING)

        assert len(readings) == 1

    def test_a_longer_source_is_read_no_more_often(
        self,
        config: Config,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A reading per stem is what keeps the cost off the frame count and off the catalog."""
        readings = self._counted(monkeypatch)
        _reconstruct(config, _square_path(tmp_path / "short.wav", config, DETUNE_CENTS), BENDING)
        short = len(readings)

        readings.clear()
        _reconstruct(config, _square_path(tmp_path / "long.wav", config, DETUNE_CENTS, seconds=SECONDS * 3), BENDING)

        assert len(readings) == short

    def test_a_stem_carrying_no_channel_reads_nothing(
        self,
        config: Config,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        readings = self._counted(monkeypatch)
        _reconstruct(config, _square_path(tmp_path / "unread.wav", config, DETUNE_CENTS), UNBENT)

        assert not readings
