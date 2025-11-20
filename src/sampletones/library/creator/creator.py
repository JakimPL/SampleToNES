from typing import Any, Callable, Dict, List, Optional, Tuple

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName
from sampletones.constants.general import BATCH_SIZE
from sampletones.ffts import Window
from sampletones.generators import GeneratorUnion, get_generators_map
from sampletones.instructions import InstructionUnion
from sampletones.parallelization import TaskProcessor
from sampletones.utils.logger import BaseLogger
from sampletones.utils.logger import logger as default_logger

from ..data import LibraryData, LibraryFragment
from ..key import LibraryKey
from .creation import generate_instruction_batch


class LibraryCreator(TaskProcessor[Tuple[LibraryKey, LibraryData]]):
    def __init__(
        self,
        config: Config,
        window: Window,
        logger: BaseLogger = default_logger,
    ) -> None:
        super().__init__(max_workers=config.general.max_workers, logger=logger)
        self.config = config.model_copy()
        self.window: Window = window
        self.instructions: List[Tuple[GeneratorClassName, InstructionUnion]] = []
        self.batches: List[List[Tuple[GeneratorClassName, InstructionUnion]]] = []

        self.total_instructions = 0
        self.completed_instructions = 0
        self.current_instruction: Optional[str] = None

    def start(self) -> None:
        if self.running:
            self.logger.warning("Library creation is already running")
            return

        super().start()

    def _create_tasks(
        self,
    ) -> List[Tuple[List[Tuple[GeneratorClassName, InstructionUnion]], Config, Window]]:
        generators: Dict[GeneratorClassName, GeneratorUnion] = get_generators_map(self.config)

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
        all_fragments = []
        for batch_results in results:
            all_fragments.extend(batch_results)

        data: Dict[InstructionUnion, LibraryFragment] = dict(all_fragments)
        library_data = LibraryData.create(self.config, data)

        key = LibraryKey.create(self.config.library, self.window)
        return key, library_data

    def _notify_progress(self) -> None:
        self.total_instructions = len(self.instructions)

        completed_batches = self.completed_tasks
        if 0 < completed_batches <= len(self.batches):
            self.completed_instructions = sum(len(self.batches[i]) for i in range(completed_batches))

            if self.completed_instructions > 0 and self.completed_instructions <= len(self.instructions):
                generator_class_name, instruction = self.instructions[self.completed_instructions - 1]
                self.current_instruction = f"{generator_class_name.value}: {instruction}"
                self.current_item = self.current_instruction

        super()._notify_progress()
