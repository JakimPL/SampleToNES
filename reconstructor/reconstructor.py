from typing import Dict, List, Literal, Optional

import numpy as np
from tqdm.auto import tqdm

from audioio import get_audio_fragments
from config import Config
from ffts.window import Window
from generators.noise import Generator, NoiseGenerator
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
        self.state = self.create_initial_state(audio)

        if mode == "frame-wise":
            self.frame_wise(audio)
        elif mode == "generator-wise":
            self.generator_wise(audio)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return Reconstruction.from_results(self.state, self.config)

    def create_initial_state(self, fragments: np.ndarray) -> ReconstructionState:
        return ReconstructionState(
            fragment_id=0,
            fragments=fragments,
            instructions={name: [] for name in self.generators},
            approximations={name: [] for name in self.generators},
            partial_approximations={name: [] for name in self.generators},
            current_initials={name: generator.initials for name, generator in self.generators.items()},
            total_error=0.0,
        )

    def frame_wise(self, audio: np.ndarray) -> None:
        count = audio.shape[0] // self.config.frame_length
        for name, generator in self.generators.items():
            generator.reset()

        for fragment_id in tqdm(range(count)):
            self.state.fragment_id = fragment_id
            fragment = self.window.get_windowed_frame(audio, fragment_id)
            for name, generator in self.generators.items():
                self.find_best_fragment(name, fragment)
                fragment -= self.state.approximations[name][-1]

    def generator_wise(self, audio: np.ndarray) -> None:
        count = audio.shape[0] // self.config.frame_length
        for name, generator in tqdm(self.generators.items()):
            generator.reset()
            for fragment_id in range(count):
                self.state.fragment_id = fragment_id
                fragment = self.window.get_windowed_frame(audio, fragment_id)
                self.find_best_fragment(name, fragment)

            audio -= np.concatenate(self.state.approximations[name])

    def update_state(self, name: str, approximation: np.ndarray, instruction: Instruction, error: float) -> None:
        generator = self.generators[name]
        self.state.approximations[name].append(approximation)
        self.state.instructions[name].append(instruction)
        self.state.total_error += error
        self.state.current_initials[name] = generator.initials

    def find_best_fragment(self, name: str, audio: np.ndarray) -> None:
        generator = self.generators[name]
        initials = self.state.current_initials[name]
        approximation, instruction, error = generator.find_best_fragment_approximation(
            audio, self.state, self.criterion, initials=initials
        )

        self.update_state(name, approximation, instruction, error)
