from typing import Callable, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.order import (
    OrderEntryViewModel,
    SequencerOrderGridViewModel,
    SequencerOrderViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.patterns.channel import Channel
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
        channels = {
            generator: self._build_channel_view(generator, song[generator]) for generator in GeneratorName.items()
        }
        position_count = max((len(view.entries) for view in channels.values()), default=0)
        return SequencerOrderGridViewModel(position_count=position_count, channels=channels)

    def push_order(self) -> None:
        self.call(self.on_order_changed, self.build_order())

    def refresh(self) -> None:
        self.push_order()

    def set_order_entry(self, generator: GeneratorName, position: int, pattern_index: int) -> None:
        self._controller.set_order_entry(generator, position, pattern_index)

    def set_master_entry(self, position: int, pattern_index: int) -> None:
        for generator in GeneratorName.items():
            self._controller.set_order_entry(generator, position, pattern_index)

    def add_to_order_all(self) -> None:
        """Appends one empty position (a ``None`` slot) to every channel's order.

        The slot holds no pattern until an index is typed into it, so the master row
        reads empty and that frame shows blank in the tracker grid; assigning an
        index later materialises the pattern on first edit.
        """
        for generator in GeneratorName.items():
            self._controller.append_to_order(generator, None)

    def remove_from_order_all(self, position: int) -> None:
        for generator in GeneratorName.items():
            self._controller.remove_from_order(generator, position)

    def _build_channel_view(
        self,
        generator: GeneratorName,
        channel: Channel,
    ) -> SequencerOrderViewModel:
        entries = tuple(
            OrderEntryViewModel(position=position, pattern_index=pattern_index)
            for position, pattern_index in enumerate(channel.order)
        )
        return SequencerOrderViewModel(
            generator=generator,
            entries=entries,
        )
