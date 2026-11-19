from typing import Callable

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.history_detail import SequencerHistoryDetail
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.tags.sequencer import TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY
from sampletones_application.utils.gui.dialogs import DialogsRenderer


class NesFrequencyChange:
    """A change of the project's NES frequency, which re-times every sample the project holds.

    A project holding samples asks before the change, until the reader opts out for the session; an
    empty project, or one whose reader opted out, takes the change at once. Canceling restores the
    field to the project's rate.

    Attributes:
        acknowledged: Whether the reader opted out of the question for this session.
    """

    def __init__(
        self,
        tracker_logic: SequencerTrackerLogic,
        project_controller: ProjectController,
        history: HistoryManager,
        history_detail: SequencerHistoryDetail,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_changed: Callable[[int], None],
    ) -> None:
        self._tracker_logic = tracker_logic
        self._project_controller = project_controller
        self._history = history
        self._history_detail = history_detail
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._on_changed = on_changed
        self.acknowledged = False

    def request(self, nes_frequency: int) -> None:
        """Applies ``nes_frequency``, asking first where the change would re-time samples."""
        if nes_frequency == self._tracker_logic.settings.nes_frequency:
            return

        if self.acknowledged or not self._project_controller.has_voices:
            self._perform(nes_frequency)
            return

        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_MODULE_DIALOG_NES_FREQUENCY,
            title=self._language_manager["global.dialog.title.change_nes_frequency"],
            message=self._language_manager["global.dialog.message.change_nes_frequency"],
            on_confirm=lambda: self._perform(nes_frequency),
            ok_label=self._language_manager["global.dialog.label.change_and_retune"],
            opt_out_label=self._language_manager["global.dialog.label.dont_ask_again"],
            on_opt_out=self._acknowledge,
            on_cancel=self._tracker_logic.push_settings,
        )

    def _perform(self, nes_frequency: int) -> None:
        """Applies the rate as one undo entry, then requests a retune of the now-stale samples.

        The entry carries a rate-keyed coalesce target so the asynchronous per-sample retune
        results fold back into this same ``SET_NES_FREQUENCY`` entry: one undo restores both the
        prior rate and the prior reconstructions, and a later change to a different rate appends
        a fresh entry.
        """
        with self._history.transaction(
            HistoryAction.SET_NES_FREQUENCY,
            detail=self._history_detail.value(nes_frequency),
            coalesce=(nes_frequency,),
        ):
            self._tracker_logic.set_nes_frequency(nes_frequency)

        self._on_changed(nes_frequency)

    def _acknowledge(self) -> None:
        self.acknowledged = True
