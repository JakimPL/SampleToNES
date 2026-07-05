from typing import Dict, List

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import FragmentedAudio

from ..approximation import ApproximationData
from .base import Selector


class GreedySelector(Selector):
    def select(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[int, Dict[GeneratorName, ApproximationData]]:
        return {fragment_id: self.reconstruct_fragment(fragmented_audio[fragment_id]) for fragment_id in fragment_ids}
