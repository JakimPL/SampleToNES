from pathlib import Path
from typing import Dict, Final, FrozenSet, List, Self, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.audio import write_wave
from sampletones_core.audio.processing import normalize
from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.constants.enums import ChannelName, GeneratorClassName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibrary, InstructionLibraryData
from sampletones_core.library.creator.creation import generate_instruction
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.corpus.paths import CATALOG_CONFIG_PATH
from sampletones_tools.corpus.synth import SynthConfig

INSTRUCTIONS_PER_GENERATOR: Final[int] = 48
CHANNELS: Final[List[ChannelName]] = [
    ChannelName.PULSE1,
    ChannelName.TRIANGLE,
    ChannelName.NOISE,
]


class ReconstructionSettings(BaseModel):
    """The settings the one in-memory library every instrument is matched against is built with."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    spectrum_method: SpectrumMethod
    transformation_gamma: int
    instructions_per_generator: int


class InstrumentSpec(BaseModel):
    """One instrument of the catalog: the voice it is rendered from and the channels it covers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    synth: str
    channels: List[ChannelName]


class CatalogSpec(BaseModel):
    """The reconstructed sample catalog: the library settings and the instruments built under them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reconstruction: ReconstructionSettings
    instruments: List[InstrumentSpec]

    @classmethod
    def load(cls) -> Self:
        """The catalog the package ships."""
        return load_yaml_model(CATALOG_CONFIG_PATH, cls)


def build_mini_library(
    config: Config,
    *,
    per_generator: int = INSTRUCTIONS_PER_GENERATOR,
) -> InstructionLibrary:
    """Builds a small in-memory instruction library covering pulse/triangle/noise.

    Candidates are sampled with an even stride across each channel's instruction
    space so pitch, volume and period are represented, rather than a biased prefix.
    """
    window = Window.from_config(config)
    extractor = get_feature_extractor(config, window)
    generators = {
        generator.class_name(): generator for generator in get_generators_by_channels(config, CHANNELS).values()
    }
    sampled: List[Tuple[GeneratorClassName, InstructionUnion]] = [
        (class_name, instruction)
        for class_name, generator in generators.items()
        for instruction in _evenly_sampled(generator.get_possible_instructions(), per_generator)
    ]
    data = dict(
        generate_instruction(generators, class_name, instruction, extractor) for class_name, instruction in sampled
    )

    library = InstructionLibrary()
    library.data[library.create_key(config, window)] = InstructionLibraryData.create(config, data)
    return library


def _evenly_sampled(candidates: Sequence[InstructionUnion], count: int) -> List[InstructionUnion]:
    stride = max(1, len(candidates) // count)
    return list(candidates[::stride][:count])


def reconstruct_sample(
    audio: np.ndarray,
    config: Config,
    library: InstructionLibrary,
    channels: FrozenSet[ChannelName],
    *,
    tmp_dir: Pathlike,
    name: str,
) -> Reconstruction:
    """Runs the real reconstruction pipeline on ``audio`` via a temp WAV.

    Raises:
        ValueError: If the reconstructor returns no reconstruction for the recording.
    """
    path = Path(tmp_dir) / f"{name}.wav"
    write_wave(path, config.library.sample_rate, audio)
    reconstruction = Reconstructor(config, channels, library=library)(path)
    if reconstruction is None:
        raise ValueError(f"Reconstruction of '{name}' produced no result")

    return reconstruction


def make_sample(
    name: str,
    audio: np.ndarray,
    config: Config,
    library: InstructionLibrary,
    *,
    tmp_dir: Pathlike,
    expected_slices: FrozenSet[ChannelName],
) -> Sample:
    """Reconstructs ``audio`` into a `Sample` playing exactly the expected channels.

    Raises:
        ValueError: If the reconstruction plays other channels than ``expected_slices``.
    """
    reconstruction = reconstruct_sample(
        audio,
        config,
        library,
        expected_slices,
        tmp_dir=tmp_dir,
        name=name,
    )
    played = frozenset(reconstruction.playing_channels)
    if played != expected_slices:
        raise ValueError(f"Sample '{name}' covers {set(played)}, expected {set(expected_slices)}")

    return Sample(name=name, reconstruction=reconstruction)


def build_catalog(
    spec: CatalogSpec,
    synth_config: SynthConfig,
    *,
    tmp_dir: Pathlike,
) -> Dict[str, Sample]:
    """Builds the reconstructed sample catalog the spec describes.

    The spec fixes the reconstruction settings (spectrum method, gamma, library size) shared by
    one in-memory library, and per instrument the voice to render and the channel slices to
    cover. Voice parameters come from ``synth_config``.

    Args:
        spec: The catalog: the library settings and the instruments.
        synth_config: The voices the instruments are rendered from.
        tmp_dir: Where the rendered recordings are written before they are reconstructed.

    Returns:
        Dict[str, Sample]: The samples, by name, in the order the spec lists them.
    """
    settings = spec.reconstruction
    library_config = InstructionsLibraryConfig(
        spectrum_method=settings.spectrum_method,
        transformation_gamma=settings.transformation_gamma,
    )
    sample_rate = library_config.sample_rate
    library = build_mini_library(
        Config(library=library_config),
        per_generator=settings.instructions_per_generator,
    )

    catalog: Dict[str, Sample] = {}
    for instrument in spec.instruments:
        config = Config(library=library_config)
        audio = _render_instrument(synth_config, instrument.synth, sample_rate=sample_rate)
        catalog[instrument.name] = make_sample(
            instrument.name,
            audio,
            config,
            library,
            tmp_dir=tmp_dir,
            expected_slices=frozenset(instrument.channels),
        )

    return catalog


def _render_instrument(
    synth_config: SynthConfig,
    name: str,
    *,
    sample_rate: int,
) -> np.ndarray:
    """Renders a named voice at peak level 1.0.

    A fresh channel seeded from the synth configuration keeps every instrument reproducible
    independently of catalog order.
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
