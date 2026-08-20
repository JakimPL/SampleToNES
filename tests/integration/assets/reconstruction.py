from pathlib import Path
from typing import Any, Dict, Final, FrozenSet, List

import numpy as np

from sampletones_core.audio import write_wave
from sampletones_core.audio.processing import normalize
from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.configs.generation import GenerationConfig
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryFragment,
)
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_yaml
from tests.integration.assets.synth_config import SynthConfig

INSTRUCTIONS_PER_GENERATOR: Final[int] = 48
CHANNELS: Final[List[ChannelName]] = [
    ChannelName.PULSE1,
    ChannelName.TRIANGLE,
    ChannelName.NOISE,
]


def build_mini_library(config: Config, *, per_generator: int = INSTRUCTIONS_PER_GENERATOR) -> InstructionLibrary:
    """Builds a small in-memory instruction library covering pulse/triangle/noise.

    Candidates are sampled with an even stride across each channel's instruction
    space so pitch, volume and period are represented, rather than a biased prefix.
    """
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    channels = get_generators_by_channels(config, CHANNELS)

    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for channel in channels.values():
        candidates = list(channel.get_possible_instructions())
        stride = max(1, len(candidates) // per_generator)
        for instruction in candidates[::stride][:per_generator]:
            data[instruction] = InstructionLibraryFragment.create(channel, instruction, extractor)

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def reconstruct_sample(
    audio: np.ndarray,
    config: Config,
    library: InstructionLibrary,
    *,
    tmp_dir: Pathlike,
    name: str,
) -> Reconstruction:
    """Runs the real reconstruction pipeline on ``audio`` via a temp WAV."""
    path = Path(tmp_dir) / f"{name}.wav"
    write_wave(path, config.library.sample_rate, audio)
    reconstruction = Reconstructor(config, library=library)(path)
    if reconstruction is None:
        raise AssertionError(f"Reconstruction of '{name}' produced no result")

    return reconstruction


def make_sample(
    name: str,
    audio: np.ndarray,
    config: Config,
    library: InstructionLibrary,
    *,
    tmp_dir: Pathlike,
    expected_slices: FrozenSet[ChannelName],
    loop: bool = False,
) -> Sample:
    """Reconstructs ``audio`` into a `Sample`, asserting the channels it plays."""
    reconstruction = reconstruct_sample(audio, config, library, tmp_dir=tmp_dir, name=name)
    played = frozenset(reconstruction.playing_channels)
    if played != expected_slices:
        raise AssertionError(f"Sample '{name}' covers {set(played)}, expected {set(expected_slices)}")

    return Sample(name=name, reconstruction=reconstruction, loop=loop)


def load_instrument_catalog(
    spec_path: Pathlike,
    synth_config: SynthConfig,
    *,
    tmp_dir: Pathlike,
) -> Dict[str, Sample]:
    """Builds the reconstructed sample catalog described by a JSON spec.

    The spec fixes the reconstruction settings (spectrum method, gamma, library
    size) shared by one in-memory library, and per instrument the synth to run and
    the channel slices to cover. Synth parameters come from ``synth_config``.
    Returns a name -> `Sample` mapping.
    """
    spec = load_yaml(spec_path)
    settings = spec["reconstruction"]
    library_config = InstructionsLibraryConfig(
        spectrum_method=SpectrumMethod(settings["spectrum_method"]),
        transformation_gamma=settings["transformation_gamma"],
    )
    sample_rate = library_config.sample_rate
    library = build_mini_library(
        Config(library=library_config),
        per_generator=settings["instructions_per_generator"],
    )

    catalog: Dict[str, Sample] = {}
    for entry in spec["instruments"]:
        channels = [ChannelName(name) for name in entry["channels"]]
        config = Config(library=library_config, generation=GenerationConfig(channels=channels))
        audio = _render_instrument(synth_config, entry["synth"], sample_rate=sample_rate)
        catalog[entry["name"]] = make_sample(
            entry["name"],
            audio,
            config,
            library,
            tmp_dir=tmp_dir,
            expected_slices=frozenset(channels),
        )

    return catalog


def _render_instrument(
    synth_config: SynthConfig,
    name: str,
    *,
    sample_rate: int,
) -> np.ndarray:
    """
    Render a named voice at peak level 1.0.

    A fresh channel seeded from the synth configuration keeps every instrument
    reproducible independently of catalog order.
    """
    voice = synth_config.voices[name]
    generator = np.random.default_rng(synth_config.seed)
    instrument: np.ndarray = normalize(
        voice.render(
            sample_rate=sample_rate,
            generator=generator,
        )
    )
    return instrument
