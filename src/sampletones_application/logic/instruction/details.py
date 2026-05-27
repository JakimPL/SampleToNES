from typing import Callable, Optional

from sampletones_application.logic.instruction.data import InstructionPanelData
from sampletones_application.logic.instruction.table_logic import InstructionDetailsLogic as _InstructionTableLogic
from sampletones_application.logic.library.manager import InstructionsLibraryManager
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.instruction.details import InstructionDetailsPanelViewModel
from sampletones_core.instructions import InstructionUnion
from sampletones_shared.utils.callbacks import CallbackMixin


class InstructionDetailsPanelLogic(CallbackMixin):
    def __init__(self, library_manager: InstructionsLibraryManager) -> None:
        self._library_manager = library_manager
        self._table_logic = _InstructionTableLogic()

        self.on_view_changed: Optional[Callable[[InstructionDetailsPanelViewModel], None]] = None
        self.on_instruction_changed: Optional[Callable[[InstructionPanelData], None]] = None

    def display_instruction(self, instruction_data: InstructionPanelData) -> None:
        self._table_logic.current_data = instruction_data
        self._emit_view()

    def clear_display(self) -> None:
        self._table_logic.clear_data()
        self._emit_view()

    def get_current_instruction_data(self) -> Optional[InstructionPanelData]:
        return self._table_logic.current_data

    def handle_instruction_parameter_changed(self, instruction: InstructionUnion) -> None:
        current = self._table_logic.current_data
        if current is not None and current.instruction == instruction:
            return

        def load() -> None:
            instruction_data = self._library_manager.load_instruction(instruction)
            self._table_logic.current_data = instruction_data
            self.call(self.on_instruction_changed, instruction_data)
            self._emit_view()

        CallbackQueue.add(load)

    def _emit_view(self) -> None:
        self.call(
            self.on_view_changed,
            InstructionDetailsPanelViewModel(
                instruction_data=self._table_logic.current_data,
                table_data=self._table_logic.get_table_data(),
            ),
        )
