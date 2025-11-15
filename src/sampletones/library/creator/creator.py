from typing import Any, Callable, Dict, List, Optional, Tuple

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName
from sampletones.constants.general import BATCH_SIZE
from sampletones.ffts import Window
from sampletones.generators import GENERATOR_CLASS_MAP, GeneratorUnion
from sampletones.instructions import InstructionUnion
from sampletones.parallelization import TaskProcessor
from sampletones.utils.logger import BaseLogger, logger

from ..data import LibraryData, LibraryFragment
from ..key import LibraryKey
from .creation import generate_instruction_batch


class LibraryCreator(TaskProcessor[Tuple[LibraryKey, LibraryData]]):
    def __init__(self, config: Config, logger: BaseLogger = logger) -> None:
        super().__init__(max_workers=config.general.max_workers, logger=logger)
        self.config = config.model_copy()
        self.window: Optional[Window] = None
        self.instructions: List[Tuple[GeneratorClassName, InstructionUnion]] = []
        self.batches: List[List[Tuple[GeneratorClassName, InstructionUnion]]] = []

        self.total_instructions = 0
        self.completed_instructions = 0
        self.current_instruction: Optional[str] = None

    def start(self, window: Window) -> None:
        if self.running:
            logger.warning("Library creation is already running")
            return

        self.window = window
        super().start()

    def _create_tasks(
        self,
    ) -> List[Tuple[List[Tuple[GeneratorClassName, InstructionUnion]], Config, Window]]:
        assert self.window is not None, "Window must be set before creating tasks"

        generators: Dict[GeneratorClassName, GeneratorUnion] = {
            name: GENERATOR_CLASS_MAP[name](self.config, name) for name in GENERATOR_CLASS_MAP
        }

        self.instructions = [
            (generator.class_name(), instruction)
            for generator in generators.values()
            for instruction in generator.get_possible_instructions()
        ]

        num_workers = max(self.max_workers, (len(self.instructions) + BATCH_SIZE - 1) // BATCH_SIZE)
        self.batches = [self.instructions[i::num_workers] for i in range(num_workers)]

        tasks = [(batch, self.config, self.window) for batch in self.batches if batch]

        return tasks

    def _get_task_function(self) -> Callable[[Tuple], List[Tuple[InstructionUnion, LibraryFragment]]]:
        return generate_instruction_batch

    def _process_results(self, results: List[Any]) -> Tuple[LibraryKey, LibraryData]:
        assert self.window is not None, "Window must be set before processing results"

        all_fragments = []
        for batch_results in results:
            all_fragments.extend(batch_results)

        data: Dict[InstructionUnion, LibraryFragment] = dict(all_fragments)
        library_data = LibraryData(config=self.config.library, data=data)

        key = LibraryKey.create(self.config.library, self.window)
        return key, library_data

    def _notify_progress(self) -> None:
        self.total_instructions = len(self.instructions)

        completed_batches = self.completed_tasks
        if completed_batches > 0 and completed_batches <= len(self.batches):
            self.completed_instructions = sum(len(self.batches[i]) for i in range(completed_batches))

            if self.completed_instructions > 0 and self.completed_instructions <= len(self.instructions):
                generator_class_name, instruction = self.instructions[self.completed_instructions - 1]
                self.current_instruction = f"{generator_class_name.value}: {instruction}"
                self.current_item = self.current_instruction

        super()._notify_progress()
