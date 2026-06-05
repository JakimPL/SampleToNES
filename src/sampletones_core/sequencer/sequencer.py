from typing import Dict

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.reconstructions import Reconstruction

from .rows.generator import GeneratorRow
from .rows.sample import SampleRow
from .sequence import Sequence


class Sequencer:
    def __init__(self) -> None:
        self.samples: Dict[str, Reconstruction] = {}
        self.sample_sequence: Sequence[SampleRow] = Sequence()
        self.generator_sequences: Dict[GeneratorName, Sequence[GeneratorRow]] = {
            name: Sequence() for name in GeneratorName
        }
