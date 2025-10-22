from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from tqdm.auto import tqdm

from config import Config
from ffts.window import Window
from instructions.instruction import Instruction
from library.data import LibraryFragment
from library.fragment import Fragment, FragmentedAudio
from library.library import LibraryData
from reconstructor.approximation import ApproximationData
from reconstructor.criterion import Criterion
from reconstructor.maps import GENERATOR_CLASS_MAP, get_generator_by_instruction
from typehints.general import GeneratorClassName
from typehints.instructions import InstructionUnion


@dataclass(frozen=True)
class LibraryWorker:
    config: Config
    window: Window
    generators: Dict[str, Any]

    def __call__(
        self,
        instructions: Tuple[GeneratorClassName, Instruction],
        instructions_ids: List[int],
        show_progress: bool = False,
    ) -> LibraryData:

        data: Dict[InstructionUnion, LibraryFragment] = {}
        for idx in tqdm(instructions_ids, disable=not show_progress):
            generator_class_name, instruction = instructions[idx]
            generator = self.generators[generator_class_name]
            fragment = LibraryFragment.create(generator, instruction, self.window)
            data[instruction] = fragment

        return LibraryData(data=data)
