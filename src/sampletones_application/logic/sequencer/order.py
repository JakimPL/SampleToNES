from typing import Callable, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.order import (
    OrderEntryViewModel,
    SequencerOrderGridViewModel,
    SequencerOrderViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song import Song
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerOrderLogic(CallbackMixin):
    """Builds the order arrangement view model and exposes order mutations.

    Navigation (the current frame) is owned by :class:`SequencerGridLogic`; this
    class is only responsible for which pattern index each channel plays at every
    order position, and how to change that arrangement.
    """

    def __init__(self, project_controller: ProjectController) -> None:
        self._controller = project_controller

        self.on_order_changed: Optional[Callable[[SequencerOrderGridViewModel], None]] = None

    def build_order(self) -> SequencerOrderGridViewModel:
        song = self._controller.project.song
        channels = {generator: self._build_channel_view(generator, song) for generator in GeneratorName.items()}
        return SequencerOrderGridViewModel(position_count=song.order_length(), channels=channels)

    def push_order(self) -> None:
        self.call(self.on_order_changed, self.build_order())

    def refresh(self) -> None:
        self.push_order()

    def set_order_entry(
        self,
        generator: GeneratorName,
        position: int,
        pattern_index: Optional[int],
    ) -> None:
        self._controller.set_order_entry(generator, position, pattern_index)

    def set_master_entry(self, position: int, pattern_index: Optional[int]) -> None:
        for generator in GeneratorName.items():
            self._controller.set_order_entry(generator, position, pattern_index)

    def find_empty_frame(self, after: int) -> Optional[int]:
        """Returns the index of the first order position strictly after ``after``
        where every channel's pattern is either unassigned or contains no notes.
        Returns None if no such position exists ahead of the given frame."""
        song = self._controller.project.song
        for position in range(after + 1, song.order_length()):
            frame = song.order[position]
            if all(
                index is None or ((pattern := song.pattern(generator, index)) is not None and pattern.is_empty())
                for generator, index in frame.items()
            ):
                return position
        return None

    def add_to_order(self) -> None:
        """Appends one empty frame (all channels silent) to the order."""
        self._controller.append_frame()

    def remove_from_order(self, position: int) -> None:
        self._controller.remove_frame(position)

    def _build_channel_view(
        self,
        generator: GeneratorName,
        song: Song,
    ) -> SequencerOrderViewModel:
        entries = tuple(
            OrderEntryViewModel(
                position=position,
                pattern_index=frame.get(generator),
            )
            for position, frame in enumerate(song.order)
        )
        return SequencerOrderViewModel(
            generator=generator,
            entries=entries,
        )
