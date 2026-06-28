from __future__ import annotations

from typing import List

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod

from ..spectrum.cqt import calculate_cqt_spectrum_columns
from ..transformer import FFTTransformer
from ..window.window import Window
from .fragment import Fragment


class FragmentedAudio(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    audio: np.ndarray = Field(..., description="Original audio data")
    fragments: List[Fragment] = Field(..., description="List of audio fragments")
    config: Config = Field(..., description="Configuration")

    @classmethod
    def create(cls, audio: np.ndarray, config: Config, window: Window) -> FragmentedAudio:
        length = (audio.shape[0] // window.frame_length) * window.frame_length
        audio = audio[:length].copy()
        count = length // window.frame_length

        match SpectrumMethod(config.library.spectrum_method):
            case SpectrumMethod.CQT:
                fragments = cls._create_cqt_fragments(audio, config, window, count)
            case _:
                fragments = [
                    Fragment.create(
                        config,
                        window.get_windowed_frame(audio, fragment_id * window.frame_length),
                        window,
                    )
                    for fragment_id in range(count)
                ]

        return cls(audio=audio, fragments=fragments, config=config)

    @classmethod
    def _create_cqt_fragments(
        cls,
        audio: np.ndarray,
        config: Config,
        window: Window,
        count: int,
    ) -> List[Fragment]:
        """
        Build CQT fragments from a single whole-signal transform.

        The constant-Q window spans several frames, so a per-fragment CQT reports each
        frame's content offset by roughly half that window. Transforming the whole
        signal once (one column per frame, librosa-centered) keeps every frame aligned
        to its own time position; column ``i`` is then attached to fragment ``i``.
        """
        if count == 0:
            return []

        transformer = FFTTransformer.from_gamma(
            config.library.transformation_gamma,
            config.library.sample_rate,
            config.library.spectrum_method,
        )
        spectra = calculate_cqt_spectrum_columns(audio, config.library.sample_rate, window.frame_length)
        return [
            Fragment.with_feature(
                config,
                window.get_windowed_frame(audio, fragment_id * window.frame_length),
                window,
                transformer.forward(spectra[fragment_id]),
            )
            for fragment_id in range(count)
        ]

    def __getitem__(self, index: int) -> Fragment:
        return self.fragments[index]

    def __setitem__(self, index: int, value: Fragment) -> None:
        self.fragments[index] = value

    def __len__(self) -> int:
        return len(self.fragments)

    @property
    def fragments_ids(self) -> List[int]:
        return list(range(len(self.fragments)))
