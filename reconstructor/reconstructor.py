from typing import Dict, List, Optional, Tuple

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
        self.current_phases = {name: 0.0 for name in GENERATORS}
        self.generators = {name: GENERATORS[name](config) for name in generators}
        self.state: Optional[ReconstructionState] = None

    def __call__(self, audio: np.ndarray) -> Reconstruction:
        fragments, _ = get_audio_fragments(audio, config=self.config)
        self.set_generators_fragment_length(fragments.shape[1])
        self.current_phases = {name: 0.0 for name in self.generators}
        self.state = self.create_initial_state(fragments)

        for fragment_id in tqdm(range(len(fragments))):
            self.state.fragment_id = fragment_id
            partial_approximations, partial_reconstruction, partial_instructions, error = (
                self.find_best_fragment_approximation(self.state)
            )

            self.state.approximations.append(partial_reconstruction)
            for name, instruction in partial_instructions.items():
                self.state.instructions[name].append(instruction)

            self.state.total_error += error
            self.update_phases()

            for name, partial_approximation in partial_approximations.items():
                self.state.partial_approximations[name].append(partial_approximation)

        return Reconstruction.from_results(self.state)

    def create_initial_state(self, fragments: np.ndarray) -> ReconstructionState:
        return ReconstructionState(
            fragment_id=0,
            fragments=fragments,
            instructions={name: [] for name in self.generators},
            approximations=[],
            partial_approximations={name: [] for name in self.generators},
            total_error=0.0,
        )

    def set_generators_fragment_length(self, length: int) -> None:
        for generator in self.generators.values():
            generator.criterion.set_fragment_length(length)

    def get_phases(self) -> Dict[str, float]:
        return {name: phase for name, phase in self.current_phases.items()}

    def update_phases(self) -> None:
        self.current_phases = {name: generator.phase for name, generator in self.generators.items()}

    def find_best_fragment_approximation(
        self, state: ReconstructionState
    ) -> Tuple[Dict[str, np.ndarray], np.ndarray, Dict[str, Instruction], float]:
        fragment = state.fragments[state.fragment_id]
        audio = fragment.copy()
        approximation = np.zeros_like(fragment)

        initial_phase = self.get_phases()
        instructions = {}
        total_error = 0.0
        partial_approximations = {}

        for name, generator in self.generators.items():
            phase = initial_phase[name]
            partial_approximation, instruction, error = generator.find_best_fragment_approximation(
                audio, self.state, initial_phase=phase
            )

            instructions[name] = instruction
            initial_phase[name] = generator.phase

            approximation += partial_approximation
            audio -= partial_approximation
            total_error += error

            partial_approximations[name] = partial_approximation

        return partial_approximations, approximation, instructions, total_error
