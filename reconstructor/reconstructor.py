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
from reconstructor.approximation import FragmentApproximation
from reconstructor.criterion import Criterion
from reconstructor.fragment import Fragment, FragmentedAudio
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
        self.state = ReconstructionState.create(list(self.generators))
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

        for fragment_id, feature in enumerate(tqdm(fragments)):
            for name, generator in self.generators.items():
                fragment_approximation = self.find_best_fragment(name, feature)
                fragments[fragment_id] -= fragment_approximation.fragment

    def generator_wise(self, fragments: FragmentedAudio) -> None:
        for name, generator in tqdm(self.generators.items()):
            generator.reset()
            for fragment_id, fragment in enumerate(fragments):
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
