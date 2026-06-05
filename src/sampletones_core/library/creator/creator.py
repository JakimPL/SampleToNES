from typing import Any, Callable, Dict, List, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Window
from sampletones_core.generators import GeneratorUnion, get_generators_map
from sampletones_core.instructions import InstructionUnion
from sampletones_core.parallelization import TaskProcessor
from sampletones_shared.logger import LoggerProtocol
from sampletones_shared.logger import logger as default_logger

from ..data import InstructionLibraryData
from ..fragment import InstructionLibraryFragment
from ..key import InstructionLibraryKey
from .creation import generate_single_instruction_task


class InstructionsLibraryCreator(TaskProcessor[Tuple[InstructionLibraryKey, InstructionLibraryData]]):
    def __init__(
        self,
        config: Config,
        window: Window,
        logger: LoggerProtocol = default_logger,
    ) -> None:
        super().__init__(max_workers=config.general.max_workers, logger=logger)
        self.config = config.model_copy()
        self.window: Window = window
        self.instructions: List[Tuple[GeneratorClassName, InstructionUnion]] = []

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
    ) -> List[Tuple[Tuple[GeneratorClassName, InstructionUnion], Config, Window]]:
        generators: Dict[GeneratorClassName, GeneratorUnion] = get_generators_map(self.config)

        self.instructions = [
            (generator.class_name(), instruction)
            for generator in generators.values()
            for instruction in generator.get_possible_instructions()
        ]

        return [(instruction_pair, self.config, self.window) for instruction_pair in self.instructions]

    def _get_task_function(
        self,
    ) -> Callable[
        [Tuple[Tuple[GeneratorClassName, InstructionUnion], Config, Window]],
        Tuple[InstructionUnion, InstructionLibraryFragment[Any]],
    ]:
        return generate_single_instruction_task

    def _process_results(
        self,
        results: List[Any],
    ) -> Tuple[InstructionLibraryKey, InstructionLibraryData]:
        data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = dict(results)
        library_data = InstructionLibraryData.create(self.config, data)

        key = InstructionLibraryKey.create(self.config.library, self.window)
        return key, library_data

    def _notify_progress(self) -> None:
        self.total_instructions = len(self.instructions)
        self.completed_instructions = self.completed_tasks

        if 0 < self.completed_tasks <= len(self.instructions):
            generator_class_name, instruction = self.instructions[self.completed_tasks - 1]
            self.current_instruction = f"{generator_class_name.value}: {instruction}"
            self.current_item = self.current_instruction

        super()._notify_progress()
