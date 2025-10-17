from typing import Dict, List, Literal, Optional

import numpy as np
from tqdm.auto import tqdm

from config import Config
from ffts.window import Window
from generators.generator import Generator
from generators.noise import NoiseGenerator
from generators.square import SquareGenerator
from generators.triangle import TriangleGenerator
from instructions.noise import NoiseInstruction
from instructions.square import SquareInstruction
from instructions.triangle import TriangleInstruction
from library.fragment import Fragment, FragmentedAudio
from library.library import Library, LibraryData
from reconstructor.approximation import FragmentApproximation
from reconstructor.criterion import Criterion
from reconstructor.reconstruction import Reconstruction
from reconstructor.state import ReconstructionState

GENERATOR_CLASSES = {
    "triangle": TriangleGenerator,
    "noise": NoiseGenerator,
    "square1": SquareGenerator,
    "square2": SquareGenerator,
}

INSTRUCTION_TO_GENERATOR_MAP = {
    TriangleInstruction: TriangleGenerator,
    SquareInstruction: SquareGenerator,
    NoiseInstruction: NoiseGenerator,
}


class Reconstructor:
    def __init__(self, config: Config, generator_names: List[str] = None) -> None:
        self.config: Config = config
        self.state: Optional[ReconstructionState] = None

        default_generators = list(GENERATOR_CLASSES.keys())
        generator_names = generator_names or default_generators
        self.generators: Dict[str, Generator] = {
            name: GENERATOR_CLASSES[name](config, name) for name in generator_names
        }

        self.window: Window = Window(config)
        self.criterion: Criterion = Criterion(config, self.window)

        self.library: LibraryData = self.load_library()

    def __call__(
        self, audio: np.ndarray, mode: Literal["frame-wise", "generator-wise"] = "frame-wise"
    ) -> Reconstruction:
        self.state = ReconstructionState.create(list(self.generators.keys()))
        fragments = self.get_fragments(audio)

        if mode == "frame-wise":
            self.frame_wise(fragments)
        elif mode == "generator-wise":
            self.generator_wise(fragments)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return Reconstruction.from_results(self.state, self.config)

    def load_library(self) -> LibraryData:
        library = Library.load()
        return library.get(self.config, self.window)

    def get_fragments(self, audio: np.ndarray) -> FragmentedAudio:
        return FragmentedAudio.create(audio, self.window)

    def frame_wise(self, fragments: FragmentedAudio) -> None:
        for fragment_id in tqdm(range(len(fragments))):
            for name, generator in self.generators.items():
                fragment = fragments[fragment_id]
                fragment_approximation = self.find_best_fragment(name, fragment)
                fragments[fragment_id] -= fragment_approximation.fragment

    def generator_wise(self, fragments: FragmentedAudio) -> None:
        for name, generator in tqdm(self.generators.items()):
            generator.reset()
            for fragment_id in tqdm(range(len(fragments))):
                fragment = fragments[fragment_id]
                fragment_approximation = self.find_best_fragment(name, fragment)
                fragments[fragment_id] -= fragment_approximation.fragment

    def update_state(self, fragment_approximation: FragmentApproximation) -> None:
        self.state.append(fragment_approximation)
