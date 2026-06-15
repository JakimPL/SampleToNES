from typing import Callable, Optional, Tuple

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.order import OrderEntryViewModel, SequencerOrderViewModel
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.patterns.channel import Channel
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerOrderLogic(CallbackMixin):
    """Builds the per-channel order view models and exposes order mutations.

    Navigation (current frame) is owned by :class:`SequencerGridLogic`; this
    class is only responsible for what patterns are in each channel's order and
    how to change that arrangement.
    """

    def __init__(self, project_controller: ProjectController) -> None:
        self._controller = project_controller

        self.on_order_changed: Optional[Callable[[Tuple[SequencerOrderViewModel, ...]], None]] = None

    def build_order(self) -> Tuple[SequencerOrderViewModel, ...]:
        song = self._controller.project.song
        return tuple(self._build_channel_view(generator, song[generator]) for generator in GeneratorName.items())

    def push_order(self) -> None:
        self.call(self.on_order_changed, self.build_order())

    def refresh(self) -> None:
        self.push_order()

    # ------------------------------------------------------------------
    # Phase 4 stubs — order position mutations (all channels in sync)
    # ------------------------------------------------------------------

    def add_to_order_all(self) -> None:
        """Append a new empty pattern to every channel's order."""
        raise NotImplementedError

    def insert_into_order_all(self, position: int) -> None:
        """Insert a new empty pattern before ``position`` in every channel."""
        raise NotImplementedError

    def remove_from_order_all(self, position: int) -> None:
        """Remove the order entry at ``position`` from every channel."""
        raise NotImplementedError

    def duplicate_position_all(self, position: int) -> None:
        """Duplicate the pattern at ``position`` and insert the copy after it."""
        raise NotImplementedError

    # ------------------------------------------------------------------

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
