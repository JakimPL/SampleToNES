from typing import Dict, List, Literal, Optional

import numpy as np
from tqdm.auto import tqdm

from config import Config
from ffts.fft import calculate_log_arfft, log_arfft_difference
from ffts.window import Window
from generators.generator import Generator
from generators.noise import NoiseGenerator
from generators.square import SquareGenerator
from generators.triangle import TriangleGenerator
from instructions.instruction import Instruction
from reconstructor.criterion import Criterion
from reconstructor.reconstruction import Reconstruction
from reconstructor.state import ReconstructionState

GENERATORS = {
    "triangle": TriangleGenerator,
    "noise": NoiseGenerator,
    "square1": SquareGenerator,
    "square2": SquareGenerator,
}


class Reconstructor:
    def __init__(self, config: Config, generators: Optional[List[str]] = None) -> None:
        if generators:
            assert all(generator in GENERATORS for generator in generators), "Unknown generator specified."
        else:
            generators = list(GENERATORS.keys())

        self.config: Config = config
        self.generators: Dict[str, Generator] = {name: GENERATORS[name](config, name) for name in generators}
        self.state: Optional[ReconstructionState] = None

        self.window: Window = Window(config)
        self.criterion: Criterion = Criterion(config, self.window)

    def __call__(
        self, audio: np.ndarray, mode: Literal["frame-wise", "generator-wise"] = "frame-wise"
    ) -> Reconstruction:
        self.state = ReconstructionState.create(self.generators)
        length = (audio.shape[0] // self.config.frame_length) * self.config.frame_length
        audio = audio[:length].copy()

        if mode == "frame-wise":
            self.frame_wise(audio)
        elif mode == "generator-wise":
            self.generator_wise(audio)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return Reconstruction.from_results(self.state, self.config)

    def get_spectral_features(self, audio: np.ndarray) -> np.ndarray:
        count = audio.shape[0] // self.config.frame_length
        fragments = [self.window.get_windowed_frame(audio, fragment_id) for fragment_id in range(count)]
        features = np.array([calculate_log_arfft(fragment) for fragment in fragments])
        return features

    def frame_wise(self, audio: np.ndarray) -> None:
        features = self.get_spectral_features(audio)

        for name, generator in self.generators.items():
            generator.reset()

        for fragment_id, feature in enumerate(tqdm(features)):
            for name, generator in self.generators.items():
                self.find_best_fragment(name, feature)
                features[fragment_id] = log_arfft_difference(self.state.features[name][-1], feature)

    def generator_wise(self, audio: np.ndarray) -> None:
        count = audio.shape[0] // self.config.frame_length
        for name, generator in tqdm(self.generators.items()):
            generator.reset()
            for fragment_id in range(count):
                self.state.fragment_id = fragment_id
                fragment = self.window.get_windowed_frame(audio, fragment_id)
                self.find_best_fragment(name, fragment)

            audio -= np.concatenate(self.state.approximations[name])

    def update_state(
        self, name: str, approximation: np.ndarray, instruction: Instruction, feature: np.ndarray, error: float
    ) -> None:
        generator = self.generators[name]
        self.state.approximations[name].append(approximation)
        self.state.instructions[name].append(instruction)
        self.state.features[name].append(feature)
        self.state.current_initials[name] = generator.initials
        self.state.total_error += error

    def find_best_fragment(self, name: str, feature: np.ndarray) -> None:
        generator = self.generators[name]
        initials = self.state.current_initials[name]
        approximation, instruction, feature, error = generator.find_best_fragment_approximation(
            feature, self.criterion, initials=initials
        )

        self.update_state(name, approximation, instruction, feature, error)
