from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from tqdm.auto import tqdm

from configs.library import LibraryConfig
from ffts.fft import FFTTransformer
from ffts.window import Window
from library.data import LibraryFragment
from library.library import LibraryData
from typehints.enums import GeneratorClassName
from typehints.instructions import InstructionUnion


@dataclass(frozen=True)
class LibraryWorker:
    config: LibraryConfig
    window: Window
    generators: Dict[GeneratorClassName, Any]

    def __call__(
        self,
        instructions: List[Tuple[GeneratorClassName, InstructionUnion]],
        instructions_ids: List[int],
        show_progress: bool = False,
    ) -> LibraryData:

        transformer = FFTTransformer.from_gamma(self.config.transformation_gamma)
        data: Dict[InstructionUnion, LibraryFragment] = {}
        for idx in tqdm(instructions_ids, disable=not show_progress):
            generator_class_name, instruction = instructions[idx]
            generator = self.generators[generator_class_name]
            fragment = LibraryFragment.create(generator, instruction, self.window, transformer=transformer)
            data[instruction] = fragment

        return LibraryData(config=self.config, data=data)
