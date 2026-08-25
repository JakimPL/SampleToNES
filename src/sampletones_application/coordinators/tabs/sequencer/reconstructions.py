from pathlib import Path
from typing import Callable, Optional

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.tabs.sequencer.project import OpenProjectRequirement
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.history_detail import SequencerHistoryDetail
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.logic.sequencer.voices import SequencerVoicesLogic
from sampletones_application.tags.sequencer import TAG_SEQUENCER_BROWSER_DIALOG_FREQUENCY
from sampletones_application.ui.panels.sequencer.voices.panel import GUISequencerVoicesPanel
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger


class SequencerReconstructions:
    """How a reconstruction joins the pool, or takes the place of one already in it.

    A reconstruction renders at the NES frequency it was generated at, so every gesture here
    settles that rate against the project's before it commits: equal rates go straight through,
    a mismatch the project can absorb adopts the incoming rate, and one it cannot is put to the
    reader with both rates named.

    The rate and what it times are settled in one history entry, so a single undo restores the
    project's previous rate together with the audio it was timing.
    """

    def __init__(
        self,
        browser_logic: SequencerBrowserLogic,
        tracker_logic: SequencerTrackerLogic,
        voices_logic: SequencerVoicesLogic,
        voices_panel: GUISequencerVoicesPanel,
        history: HistoryManager,
        history_detail: SequencerHistoryDetail,
        project_controller: ProjectController,
        open_project: OpenProjectRequirement,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_tab_switch: Callable[[Tab], None],
        on_sample_reconstruction_replaced: Callable[[str, Reconstruction], None],
    ) -> None:
        self._browser_logic = browser_logic
        self._tracker_logic = tracker_logic
        self._voices_logic = voices_logic
        self._voices_panel = voices_panel
        self._history = history
        self._history_detail = history_detail
        self._project_controller = project_controller
        self._open_project = open_project
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._on_tab_switch = on_tab_switch
        self._on_sample_reconstruction_replaced = on_sample_reconstruction_replaced

    def import_from_file(self, filepath: Path) -> None:
        """Reads a reconstruction file and brings what it holds into the pool as a sample."""
        if not self._open_project.met():
            return

        reconstruction = self._loaded(filepath)
        if reconstruction is None:
            return

        self._add_with_frequency_check(reconstruction, filepath.stem)

    def import_object(self, reconstruction: Reconstruction, name: str) -> None:
        """Adds an in-memory reconstruction — the one open in the Reconstruction tab — as a sample.

        The sample embeds an independent copy, so the open document keeps its own source-audio
        location and file backing while the project stores a self-contained, detached sample.
        """
        if not self._open_project.met():
            return

        self._add_with_frequency_check(
            reconstruction.model_copy(deep=True),
            name,
        )

    def replace_from_file(self, filepath: Path) -> None:
        """Substitutes the selected sample's reconstruction with a browser file's.

        The sample keeps its id and position, so every pattern row referencing it sounds the
        incoming audio while the tracker shows it where it was, and it takes the file's name the way
        an import does. The target is whatever the samples panel has selected as the gesture starts,
        which is also what named the menu item the user clicked.
        """
        selection = self._voices_panel.selection
        if selection is None:
            return

        reconstruction = self._loaded(filepath)
        if reconstruction is None:
            return

        self._reconcile_nes_frequency(
            reconstruction,
            lambda adopt_frequency: self._commit_replace(
                selection.voice_id,
                reconstruction,
                filepath.stem,
                adopt_frequency=adopt_frequency,
            ),
            can_adopt_frequency=self._project_controller.voice_count == 1,
        )

    def replace_target_label(self) -> Optional[str]:
        """The indexed label of the sample a browser replacement would overwrite, while one is selected."""
        selection = self._voices_panel.selection
        if selection is None:
            return None

        return selection.label

    def _loaded(self, filepath: Path) -> Optional[Reconstruction]:
        """Reads a reconstruction file, reporting one the reader cannot take.

        Returns:
            Optional[Reconstruction]: What the file holds, or ``None`` once the failure has been
            shown.
        """
        try:
            return self._browser_logic.load_reconstruction(filepath)
        except (SampleToNESError, OSError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to load reconstruction from {filepath}",
            )
            self._dialogs.show_error(exception)

        return None

    def _add_with_frequency_check(
        self,
        reconstruction: Reconstruction,
        name: str,
    ) -> None:
        """Adds a loaded reconstruction once its NES frequency is settled against the project's.

        An empty project adopts the incoming frequency, since the rate times nothing there yet; a
        project that already holds samples confirms first, because the rate governs how all of them
        play back.
        """
        self._reconcile_nes_frequency(
            reconstruction,
            lambda adopt_frequency: self._commit_add(
                reconstruction,
                name,
                adopt_frequency=adopt_frequency,
            ),
            can_adopt_frequency=not self._project_controller.has_voices,
        )

    def _reconcile_nes_frequency(
        self,
        reconstruction: Reconstruction,
        commit: Callable[[Optional[int]], None],
        *,
        can_adopt_frequency: bool,
    ) -> None:
        """Settles a reconstruction's NES frequency against the project's, then commits the gesture.

        A reconstruction renders at the frequency it was generated at, so bringing one recorded at
        another rate into the project plays it back wrong. Equal rates commit straight away. A
        mismatch the project can absorb — because the rate times nothing that outlives the gesture —
        adopts the incoming rate. Otherwise the user decides, seeing both rates, and confirming
        keeps the project's rate for the samples already timed by it.

        Args:
            reconstruction: The reconstruction being brought into the project.
            commit: Performs the gesture, receiving the frequency to adopt, or ``None`` to keep the
                project's.
            can_adopt_frequency: Whether adopting the incoming rate re-times only what this gesture
                itself brings in, which settles a mismatch without asking.
        """
        reconstruction_frequency = reconstruction.config.nes_frequency
        project_frequency = self._tracker_logic.settings.nes_frequency

        if reconstruction_frequency == project_frequency:
            commit(None)
            return

        if can_adopt_frequency:
            commit(reconstruction_frequency)
            return

        self._dialogs.show_confirmation(
            tag=TAG_SEQUENCER_BROWSER_DIALOG_FREQUENCY,
            title=self._language_manager["global.dialog.title.frequency_mismatch"],
            message=self._language_manager["global.dialog.message.frequency_mismatch"].format(
                reconstruction=reconstruction_frequency,
                project=project_frequency,
            ),
            on_confirm=lambda: commit(None),
            ok_label=self._language_manager["global.dialog.label.add_anyway"],
        )

    def _commit_add(
        self,
        reconstruction: Reconstruction,
        name: str,
        *,
        adopt_frequency: Optional[int],
    ) -> None:
        """Adds a reconstruction as one undoable gesture, optionally adopting its frequency.

        The frequency reconciliation and the sample insertion form a single history
        entry, so undoing a freshly-imported sample also restores the prior rate.
        """
        with self._history.transaction(
            HistoryAction.ADD_SAMPLE,
            detail=self._history_detail.add_sample(name),
        ):
            if adopt_frequency is not None:
                self._tracker_logic.set_nes_frequency(adopt_frequency)
            self._browser_logic.add_reconstruction(reconstruction, name)

        self._on_tab_switch(Tab.SEQUENCER)

    def _commit_replace(
        self,
        voice_id: str,
        reconstruction: Reconstruction,
        name: str,
        *,
        adopt_frequency: Optional[int],
    ) -> None:
        """Substitutes a sample's reconstruction as one undoable gesture, renaming it to the source.

        The detail is composed while the sample still holds the outgoing reconstruction, so it reads
        the name being replaced alongside the incoming one. The replacement is announced in the same
        window, ahead of the substitution, because an editor holding the sample open recognizes it by
        the identity of the reconstruction it is about to give up. The frequency adoption, the rename,
        and the substitution share a single history entry, so one undo restores the previous rate,
        name, and audio together.
        """
        detail = self._history_detail.replace_sample(voice_id, name)
        with self._history.transaction(
            HistoryAction.REPLACE_SAMPLE,
            detail=detail,
        ):
            if adopt_frequency is not None:
                self._tracker_logic.set_nes_frequency(adopt_frequency)

            self._voices_logic.rename_voice(voice_id, name)
            self._on_sample_reconstruction_replaced(voice_id, reconstruction)
            self._browser_logic.replace_reconstruction(voice_id, reconstruction)
