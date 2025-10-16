from typing import Dict, Literal, Optional

import numpy as np
from tqdm.auto import tqdm

from config import Config
from ffts.window import Window
from generators.types import GeneratorClassName
from library.fragment import Fragment, FragmentedAudio
from library.library import Library, LibraryKey
from reconstructor.approximation import FragmentApproximation
from reconstructor.criterion import Criterion
from reconstructor.reconstruction import Reconstruction
from reconstructor.state import ReconstructionState

GENERATOR_CLASSES = {
    "triangle": "TriangleGenerator",
    "noise": "NoiseGenerator",
    "square1": "SquareGenerator",
    "square2": "SquareGenerator",
}


class Reconstructor:
    def __init__(self, config: Config, generator_names: Optional[Dict[str, GeneratorClassName]] = None) -> None:
        self.config: Config = config

        self.generator_names: Dict[str, GeneratorClassName] = (
            generator_names if generator_names is not None else GENERATOR_CLASSES.copy()
        )
        self.state: Optional[ReconstructionState] = None

        self.window: Window = Window(config)
        self.criterion: Criterion = Criterion(config, self.window)
        self.key = LibraryKey.create(config, self.window)

        self.library: Library = Library.load()

    def __call__(
        self, audio: np.ndarray, mode: Literal["frame-wise", "generator-wise"] = "frame-wise"
    ) -> Reconstruction:
        self.state = ReconstructionState.create(list(self.generator_names.keys()))
        fragments = self.get_fragments(audio)

        if mode == "frame-wise":
            self.frame_wise(fragments)
        elif mode == "generator-wise":
            self.generator_wise(fragments)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return Reconstruction.from_results(self.state, self.config)

    def get_fragments(self, audio: np.ndarray) -> FragmentedAudio:
        return FragmentedAudio.create(audio, self.window)

    def frame_wise(self, fragments: FragmentedAudio) -> None:
        for name, generator in self.generators.items():
            generator.reset()

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

    def find_best_fragment(self, name: str, fragment: Fragment) -> FragmentApproximation:
        generator = self.generators[name]
        initials = self.state.initials[name]
        fragment_approximation = generator.find_best_fragment_approximation(fragment, self.criterion, initials=initials)
        self.update_state(fragment_approximation)
        return fragment_approximation
