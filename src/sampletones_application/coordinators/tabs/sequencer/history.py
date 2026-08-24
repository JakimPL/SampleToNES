from typing import Callable, Optional, ParamSpec

from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.history.transaction import CoalesceKey
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.view_model.sequencer.history import (
    HistoryEntryViewModel,
    HistoryViewModel,
)
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.shared.history import HistoryDetail
from sampletones_core.constants.enums import ChannelName

_GestureParams = ParamSpec("_GestureParams")


class SequencerHistoryRecorder:
    """The path every sequencer gesture takes into the project history.

    A gesture is handed here as the callback the panel fires, and comes back wrapped in the
    transaction that records the single entry undoing it. What that entry says, and which target
    it coalesces onto, are computed from the very arguments the gesture receives, so a hook keeps
    the signature its panel calls it with.

    The panel's own view of the stack is built here too, since the labels an entry prints and the
    action it was recorded under are read from the same place.
    """

    def __init__(
        self,
        history: HistoryManager,
        project_controller: ProjectController,
        tracker_logic: SequencerTrackerLogic,
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._history = history
        self._project_controller = project_controller
        self._tracker_logic = tracker_logic
        self._language_manager = language_manager

    def undoable(
        self,
        action: HistoryAction,
        callback: Callable[_GestureParams, None],
        *,
        detail: Optional[Callable[_GestureParams, HistoryDetail]] = None,
        coalesce: Optional[Callable[_GestureParams, CoalesceKey]] = None,
    ) -> Callable[_GestureParams, None]:
        """Wraps a state-changing hook so its whole gesture becomes one undo entry.

        Every mutation the wrapped callback triggers is grouped under ``action``;
        a gesture that changes nothing records no entry. ``detail`` computes the
        entry's colored description segments from the same arguments the hook
        receives, and ``coalesce`` computes the gesture's target key from them:
        consecutive gestures sharing the same action and target collapse into a
        single entry.

        The gesture is batched inside its transaction, so however many rows it
        writes, the panels rebuild once — and they rebuild before the entry that
        undoes them is recorded, because the snapshot reads the project rather
        than the views.
        """

        def wrapped(
            *args: _GestureParams.args,
            **kwargs: _GestureParams.kwargs,
        ) -> None:
            description = detail(*args, **kwargs) if detail is not None else ()
            key = coalesce(*args, **kwargs) if coalesce is not None else None
            with (
                self._history.transaction(
                    action,
                    detail=description,
                    coalesce=key,
                ),
                self._project_controller.batch(),
            ):
                callback(*args, **kwargs)

        return wrapped

    def cell_key(
        self,
        row_index: int,
        channel: Optional[ChannelName],
    ) -> CoalesceKey:
        """Identifies one cell of the displayed frame as a coalescing target.

        The sample column (``channel`` absent) is its own target, distinct from
        every channel column.
        """
        channel_key = channel if channel is not None else ""
        return (self._tracker_logic.frame_index, channel_key, row_index)

    def note_key(
        self,
        row_index: int,
        channel: ChannelName,
        _pitch: int,
    ) -> CoalesceKey:
        """Identifies the cell a typed note landed in, so retyping one note coalesces onto it."""
        return self.cell_key(row_index, channel)

    def adjustment_key(
        self,
        region: TrackerRegion,
        _delta: int,
    ) -> CoalesceKey:
        """Identifies the cells an adjustment covers as one coalescing target.

        A streak of nudges over the same block reads as one entry, so holding a transpose key steps
        the selection and leaves a single step to undo; moving the cursor or reaching the selection
        out starts the next one.
        """
        return (
            self._tracker_logic.frame_index,
            region.first_row,
            region.last_row,
            region.first_slot,
            region.last_slot,
        )

    def edit_row_key(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        voice_id: Optional[str],
        transpose: Optional[int],
        volume: Optional[int],
    ) -> CoalesceKey:
        """Extends the cell target with the subcolumns the edit writes.

        Consecutive edits of one cell coalesce only when they write the same
        subcolumns, so entering a note and then tweaking its volume stay
        separate entries.
        """
        return (
            *self.cell_key(row_index, channel),
            voice_id is not None,
            transpose is not None,
            volume is not None,
        )

    def module_setting_key(self, _value: int) -> CoalesceKey:
        """Marks a module-wide setting as one target, shared by its whole streak."""
        return ()

    def view_model(self) -> HistoryViewModel:
        """The stack as the history panel draws it, each entry labeled by its action."""
        cursor = self._history.cursor
        entries = tuple(
            HistoryEntryViewModel(
                index=index,
                label=self._action_label(entry.action),
                detail_segments=entry.detail,
                is_current=index == cursor,
                is_future=index > cursor,
            )
            for index, entry in enumerate(self._history.entries)
        )
        return HistoryViewModel(entries=entries, cursor=cursor)

    def _action_label(self, action: HistoryAction) -> str:
        return self._language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            action,
        ]
