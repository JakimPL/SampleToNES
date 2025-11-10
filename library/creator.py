from typing import Any, Callable, Dict, List, Optional, Tuple

from configs.config import Config
from configs.library import LibraryConfig
from constants.enums import GeneratorClassName
from ffts.fft import FFTTransformer
from ffts.window import Window
from library.data import LibraryData, LibraryFragment
from library.key import LibraryKey
from reconstructor.maps import GENERATOR_CLASS_MAP
from typehints.generators import GeneratorUnion
from typehints.instructions import InstructionUnion
from utils.logger import logger
from utils.parallelization.processor import TaskProcessor


def process_instruction(
    task: Tuple[Tuple[GeneratorClassName, InstructionUnion], LibraryConfig, Window, Dict[GeneratorClassName, Any]],
) -> Tuple[InstructionUnion, LibraryFragment]:
    (generator_class_name, instruction), config, window, generators = task
    transformer = FFTTransformer.from_gamma(config.transformation_gamma)
    generator = generators[generator_class_name]
    fragment = LibraryFragment.create(generator, instruction, window, transformer=transformer)
    return instruction, fragment


class LibraryCreator(TaskProcessor[Tuple[LibraryKey, LibraryData]]):
    def __init__(self, config: Config) -> None:
        super().__init__(max_workers=config.general.max_workers)
        self.config = config.model_copy()
        self.window: Optional[Window] = None
        self.generators: Dict[GeneratorClassName, GeneratorUnion] = {}
        self.instructions: List[Tuple[GeneratorClassName, InstructionUnion]] = []

        self.total_instructions = 0
        self.completed_instructions = 0
        self.current_instruction: Optional[str] = None

    def start(self, window: Window, overwrite: bool = False) -> None:
        if self.running:
            logger.warning("Library creation is already running")
            return

        self.window = window
        super().start()

    def _create_tasks(
        self,
    ) -> List[Tuple[Tuple[GeneratorClassName, InstructionUnion], LibraryConfig, Window, Dict[GeneratorClassName, Any]]]:
        assert self.window is not None, "Window must be set before creating tasks"

        self.generators = {name: GENERATOR_CLASS_MAP[name](self.config, name) for name in GENERATOR_CLASS_MAP}

        self.instructions = [
            (generator.class_name(), instruction)
            for generator in self.generators.values()
            for instruction in generator.get_possible_instructions()
        ]

        tasks = [
            (instruction_data, self.config.library, self.window, self.generators)
            for instruction_data in self.instructions
        ]

        return tasks

    def _get_task_function(self) -> Callable[[Tuple], Tuple[InstructionUnion, LibraryFragment]]:
        return process_instruction

    def _process_results(self, results: List[Any]) -> Tuple[LibraryKey, LibraryData]:
        assert self.window is not None, "Window must be set before processing results"

        data: Dict[InstructionUnion, LibraryFragment] = dict(results)
        library_data = LibraryData(config=self.config.library, data=data)

        key = LibraryKey.create(self.config.library, self.window)
        return key, library_data

    def _notify_progress(self) -> None:
        self.total_instructions = self.total_tasks
        self.completed_instructions = self.completed_tasks
        if self.completed_tasks > 0 and self.completed_tasks <= len(self.instructions):
            generator_class_name, instruction = self.instructions[self.completed_tasks - 1]
            self.current_instruction = f"{generator_class_name.value}: {instruction}"
            self.current_item = self.current_instruction

        super()._notify_progress()
