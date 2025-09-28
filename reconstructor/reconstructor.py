from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
from tqdm.auto import tqdm

from audioio import get_audio_fragments
from config import Config
from generators.noise import NoiseGenerator
from generators.square import SquareGenerator
from generators.triangle import TriangleGenerator
from instructions.instruction import Instruction
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

        self.config = config
        self.generators = {name: GENERATORS[name](name, config) for name in generators}
        self.state: Optional[ReconstructionState] = None

    def __call__(self, audio: np.ndarray, mode: Literal["single-pass", "multi-pass"] = "multi-pass") -> Reconstruction:
        fragments, _ = get_audio_fragments(audio, config=self.config)
        self.set_generators_fragment_length(fragments.shape[1])
        self.state = self.create_initial_state(fragments)

        if mode == "single-pass":
            self.single_pass(fragments)
        elif mode == "multi-pass":
            self.multi_pass(fragments)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return Reconstruction.from_results(self.state)

    def create_initial_state(self, fragments: np.ndarray) -> ReconstructionState:
        return ReconstructionState(
            fragment_id=0,
            fragments=fragments,
            instructions={name: [] for name in self.generators},
            approximations={name: [] for name in self.generators},
            partial_approximations={name: [] for name in self.generators},
            current_phases={name: 0.0 for name in self.generators},
            current_clocks={name: self.generators[name].clock for name in self.generators},
            total_error=0.0,
        )

    def set_generators_fragment_length(self, length: int) -> None:
        for generator in self.generators.values():
            generator.criterion.set_fragment_length(length)

    def single_pass(self, fragments: np.ndarray) -> None:
        for name, generator in self.generators.items():
            generator.reset()
            for fragment_id in tqdm(range(len(fragments))):
                self.find_best_fragment(name, fragments, fragment_id)

    def multi_pass(self, fragments: np.ndarray) -> None:
        audio = np.concatenate(fragments)
        for name, generator in tqdm(self.generators.items()):
            generator.reset()
            self.state.approximations = []
            for fragment_id in range(len(fragments)):
                self.find_best_fragment(name, fragments, fragment_id)

            audio -= np.concatenate(self.state.approximations)
            fragments, _ = get_audio_fragments(audio, config=self.config)

    def update_state(self, name: str, approximation, instruction, error) -> None:
        generator = self.generators[name]
        self.state.approximations[name].append(approximation)
        self.state.instructions[name].append(instruction)
        self.state.total_error += error
        self.state.current_phases[name] = generator.phase
        self.state.current_clocks[name] = generator.clock

    def find_best_fragment(self, name: str, fragments, fragment_id):
        generator = self.generators[name]
        self.state.fragment_id = fragment_id
        fragment = fragments[fragment_id].copy()
        phase = self.state.current_phases[name]
        clock = self.state.current_clocks[name]
        approximation, instruction, error = generator.find_best_fragment_approximation(
            fragment, self.state, initial_phase=phase, initial_clock=clock
        )

        self.update_state(name, approximation, instruction, error)
