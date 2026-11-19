from typing import Final, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.tabs.reconstruction.coordinator import (
    ReconstructionTabCoordinator,
)
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.instruments import (
    ReconstructionInstrumentsLogic,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.queue import ReconstructionRewrites
from sampletones_application.logic.reconstruction.rewrites.steps import RateChange
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_core.constants.audio import START_OF_AUDIO
from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import SILENT_VOLUME
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from tests.conftest import RENDER_BUDGET
from tests.suite.envelopes import exported, land_envelopes
from tests.suite.history.wiring import wired_history
from tests.suite.regeneration import HeldRegeneration
from tests.suite.stems import (
    SHARED_CHANNEL,
    SHARED_OWNERS,
    SOLE_CHANNEL,
    STEM_B_ID,
    regenerated,
    taking_turns,
)

KEY_POSITION: Final[int] = 735
HISTORY_BUDGET: Final[int] = 16
TYPED_VOLUME: Final[Tuple[int, ...]] = (6, 6)
RETIMED_FREQUENCY: Final[int] = 50
OPEN_VOICE_ID: Final[str] = "lead-id"

__all__ = ["taking_turns"]


class TestAudioDataChanged:
    """The reconstruction player mirrors the loaded reconstruction: fresh audio replaces the
    player's data and a cleared reconstruction empties the player."""

    def test_new_audio_loads_into_the_player(self) -> None:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_player_logic = MagicMock()
        audio_data = MagicMock()

        instance._on_audio_data_changed(audio_data)

        instance._reconstruction_player_logic.load_audio_data.assert_called_once_with(audio_data)
        instance._reconstruction_player_logic.clear_audio.assert_not_called()

    def test_cleared_audio_empties_the_player(self) -> None:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_player_logic = MagicMock()

        instance._on_audio_data_changed(None)

        instance._reconstruction_player_logic.clear_audio.assert_called_once_with()
        instance._reconstruction_player_logic.load_audio_data.assert_not_called()


class TestTheMarkOfAKey:
    """The note a key struck on the tab carries the plot card's mark, which comes off once the note ends."""

    def test_a_note_sounding_marks_where_it_stands(self) -> None:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_plot_panel = MagicMock()

        instance._follow_key(KEY_POSITION)

        instance._reconstruction_plot_panel.set_playback_position.assert_called_once_with(KEY_POSITION)

    def test_a_note_ended_takes_the_mark_off(self) -> None:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_plot_panel = MagicMock()

        instance._follow_key(None)

        instance._reconstruction_plot_panel.set_playback_position.assert_called_once_with(START_OF_AUDIO)


class TestTheTabAsksForItsDocumentToChange:
    """A rate the reader types reaches the document as a step of its own."""

    @pytest.fixture
    def requests(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def coordinator(self, requests: MagicMock) -> ReconstructionTabCoordinator:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._on_rewrite_requested = requests
        return instance

    def test_a_typed_rate_asks_for_the_document_to_be_re_timed(
        self,
        coordinator: ReconstructionTabCoordinator,
        requests: MagicMock,
    ) -> None:
        coordinator._request_rate_change(RETIMED_FREQUENCY)

        requests.assert_called_once_with(RateChange(nes_frequency=RETIMED_FREQUENCY))


class TestUpdateReconstructionRefitsTheWaveformOnRequest:
    """A retune moves the audio's own length, so the caller that knows this asks the waveform to
    re-fit; an ordinary edit leaves the reader's view where it was, as it always has."""

    @staticmethod
    def _coordinator() -> ReconstructionTabCoordinator:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_panel_logic = MagicMock()
        instance._reconstruction_instruments_logic = MagicMock()
        return instance

    def test_a_retune_is_forwarded_to_the_panel_logic(self) -> None:
        coordinator = self._coordinator()

        coordinator.update_reconstruction(refit_waveform=True)

        coordinator._reconstruction_panel_logic.update_reconstruction.assert_called_once_with(refit_waveform=True)

    def test_an_ordinary_call_asks_for_no_refit(self) -> None:
        coordinator = self._coordinator()

        coordinator.update_reconstruction()

        coordinator._reconstruction_panel_logic.update_reconstruction.assert_called_once_with(refit_waveform=False)

    def test_a_redraw_asks_for_no_refit(self) -> None:
        coordinator = self._coordinator()

        coordinator.redraw_reconstruction(refit_waveform=False)

        coordinator._reconstruction_panel_logic.update_reconstruction.assert_called_once_with(refit_waveform=False)

    def test_a_redraw_at_another_rate_is_forwarded_to_the_panel_logic(self) -> None:
        """An undo or a replacement can bring a document timed at another rate, which spans another length."""
        coordinator = self._coordinator()

        coordinator.redraw_reconstruction(refit_waveform=True)

        coordinator._reconstruction_panel_logic.update_reconstruction.assert_called_once_with(refit_waveform=True)


class TestTheInstrumentsPanelDrawsTheDocument:
    """A document rewritten outside the instruments panel is drawn as it stands, and one the panel's
    own edit rebuilt keeps the envelopes the panel draws."""

    @pytest.fixture
    def reconstruction(self, taking_turns: Reconstruction) -> Reconstruction:
        return taking_turns

    @pytest.fixture
    def reconstruction_manager(
        self,
        reconstruction: Reconstruction,
        scheduling: SchedulingBehavior,
    ) -> ReconstructionManager:
        manager = ReconstructionManager(scheduling=scheduling, renders=RenderCache(budget_bytes=RENDER_BUDGET))
        manager.load_reconstruction_object(reconstruction, name="lead", voice_id=OPEN_VOICE_ID)
        land_envelopes(manager)
        return manager

    @pytest.fixture
    def instruments_logic(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> ReconstructionInstrumentsLogic:
        """The panel's logic over the editor the application builds, reading the open document."""
        controller = ProjectController(ProjectManager())
        editor = InstrumentEditor(
            reconstruction_manager,
            controller,
            wired_history(controller, budget=HISTORY_BUDGET, strict=True),
            lambda _voice_id, _feature_key: (),
        )
        return ReconstructionInstrumentsLogic(
            editor,
            ReconstructionRewrites(reconstruction_manager, HeldRegeneration()),
        )

    @pytest.fixture
    def drawn(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
    ) -> List[Optional[ChannelEnvelopesViewModel]]:
        """Every set of envelopes the panel is handed to draw."""
        drawn: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = drawn.append
        return drawn

    @pytest.fixture
    def coordinator(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
    ) -> ReconstructionTabCoordinator:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._reconstruction_panel_logic = MagicMock()
        instance._reconstruction_instruments_logic = instruments_logic
        return instance

    @staticmethod
    def _remove(
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
    ) -> None:
        """A removal landing on the open document the way the coordinator lands it, and the listening it owes."""
        reconstruction_manager.apply_edited(without_stem(reconstruction, STEM_B_ID), None)
        coordinator.redraw_reconstruction(refit_waveform=False)
        land_envelopes(reconstruction_manager)
        coordinator.redraw_listening(envelopes_changed=True)

    def test_a_removal_draws_no_envelopes_until_its_listening_lands(
        self,
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
        drawn: List[Optional[ChannelEnvelopesViewModel]],
    ) -> None:
        reconstruction_manager.apply_edited(without_stem(reconstruction, STEM_B_ID), None)

        coordinator.redraw_reconstruction(refit_waveform=False)

        assert drawn == [None]

    def test_a_removal_draws_the_document_it_leaves_once_its_listening_lands(
        self,
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
        drawn: List[Optional[ChannelEnvelopesViewModel]],
    ) -> None:
        self._remove(coordinator, reconstruction_manager, reconstruction)

        assert drawn[-1] is not None
        assert drawn[-1] is reconstruction_manager.current_features

    def test_a_removal_draws_the_frames_it_released_as_rests(
        self,
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
        drawn: List[Optional[ChannelEnvelopesViewModel]],
    ) -> None:
        self._remove(coordinator, reconstruction_manager, reconstruction)

        envelopes = drawn[-1]
        assert envelopes is not None
        assert envelopes[SHARED_CHANNEL].volume.items[SHARED_OWNERS.index(STEM_B_ID)] == SILENT_VOLUME

    def test_a_removal_draws_a_channel_it_emptied_standing_by(
        self,
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
        drawn: List[Optional[ChannelEnvelopesViewModel]],
    ) -> None:
        self._remove(coordinator, reconstruction_manager, reconstruction)

        envelopes = drawn[-1]
        assert envelopes is not None
        assert not envelopes[SOLE_CHANNEL].has_frames

    def test_a_regeneration_leaves_a_field_being_typed_in_alone(
        self,
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
        drawn: List[Optional[ChannelEnvelopesViewModel]],
    ) -> None:
        """The regenerated document carries what the reader typed, so the panel keeps drawing it."""
        envelopes = reconstruction_manager.current_features
        assert envelopes is not None
        typed = envelopes[SHARED_CHANNEL].with_envelope(FeatureKey.VOLUME, Envelope[int](items=TYPED_VOLUME))
        rebuilt = regenerated(reconstruction, SHARED_CHANNEL, typed)
        reconstruction_manager.apply_edited(rebuilt, exported(rebuilt, reconstruction_manager.listening.selection))

        coordinator.update_reconstruction()

        assert drawn == []


class TestTheInstrumentsPanelFollowsTheInstrument:
    """The panel keeps the instrument it edits while the project holds it, and draws a restore of it."""

    @pytest.fixture
    def project_controller(self) -> ProjectController:
        return ProjectController(ProjectManager())

    @pytest.fixture
    def history(self, project_controller: ProjectController) -> HistoryManager:
        return wired_history(project_controller, budget=HISTORY_BUDGET, strict=True)

    @pytest.fixture
    def instrument_id(self, project_controller: ProjectController, history: HistoryManager) -> str:
        with history.transaction(HistoryAction.ADD_INSTRUMENT):
            return project_controller.add_instrument(new_instrument("lead")).id

    @pytest.fixture
    def editor(self, project_controller: ProjectController, history: HistoryManager) -> InstrumentEditor:
        reconstruction_manager = MagicMock(spec=ReconstructionManager)
        reconstruction_manager.current_features = None
        return InstrumentEditor(
            reconstruction_manager,
            project_controller,
            history,
            lambda _voice_id, _feature_key: (),
        )

    @pytest.fixture
    def views(self) -> List[ReconstructionInstrumentsViewModel]:
        """Every view the panel is handed to draw."""
        return []

    @pytest.fixture
    def coordinator(
        self,
        editor: InstrumentEditor,
        views: List[ReconstructionInstrumentsViewModel],
    ) -> ReconstructionTabCoordinator:
        instruments_logic = ReconstructionInstrumentsLogic(
            editor, ReconstructionRewrites(MagicMock(), HeldRegeneration())
        )
        instruments_logic.on_view_changed = views.append
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._instrument_editor = editor
        instance._reconstruction_instruments_logic = instruments_logic
        instance._reconstruction_panel_logic = MagicMock()
        return instance

    def test_a_restore_keeping_the_instrument_draws_it(
        self,
        coordinator: ReconstructionTabCoordinator,
        editor: InstrumentEditor,
        instrument_id: str,
        views: List[ReconstructionInstrumentsViewModel],
    ) -> None:
        editor.edit_instrument(instrument_id)

        coordinator.follow_instrument(restored=True)

        assert len(views) == 1
        assert views[0].instrument is not None
        assert editor.holds_instrument

    def test_another_change_keeping_the_instrument_leaves_the_panel_as_drawn(
        self,
        coordinator: ReconstructionTabCoordinator,
        editor: InstrumentEditor,
        instrument_id: str,
        views: List[ReconstructionInstrumentsViewModel],
    ) -> None:
        """A keystroke in the tracker changes the project, and the panel keeps what the reader writes."""
        editor.edit_instrument(instrument_id)

        coordinator.follow_instrument(restored=False)

        assert views == []
        assert editor.holds_instrument

    @pytest.mark.parametrize("restored", (True, False), ids=("restored", "edited"))
    def test_an_instrument_the_project_lost_leaves_the_panel_empty(
        self,
        restored: bool,
        coordinator: ReconstructionTabCoordinator,
        editor: InstrumentEditor,
        project_controller: ProjectController,
        history: HistoryManager,
        instrument_id: str,
        views: List[ReconstructionInstrumentsViewModel],
    ) -> None:
        editor.edit_instrument(instrument_id)
        with history.transaction(HistoryAction.REMOVE_VOICE):
            project_controller.remove_voice(instrument_id)

        coordinator.follow_instrument(restored=restored)

        assert not editor.holds_instrument
        assert len(views) == 1
        assert views[0].instrument is None
        coordinator._reconstruction_panel_logic.close_reconstruction.assert_called_once_with()

    def test_a_panel_holding_no_instrument_follows_nothing(
        self,
        coordinator: ReconstructionTabCoordinator,
        views: List[ReconstructionInstrumentsViewModel],
    ) -> None:
        coordinator.follow_instrument(restored=True)

        assert views == []

    def test_closing_the_instrument_draws_the_panel_empty(
        self,
        coordinator: ReconstructionTabCoordinator,
        editor: InstrumentEditor,
        instrument_id: str,
        views: List[ReconstructionInstrumentsViewModel],
    ) -> None:
        editor.edit_instrument(instrument_id)

        coordinator.close_instrument()

        assert not editor.holds_instrument
        assert len(views) == 1
        assert views[0].instrument is None

    def test_closing_the_instrument_empties_the_waveform_card(
        self,
        coordinator: ReconstructionTabCoordinator,
        editor: InstrumentEditor,
        instrument_id: str,
    ) -> None:
        """The card draws the instrument's own audio, so the tab empties it the way a closed reconstruction does."""
        editor.edit_instrument(instrument_id)

        coordinator.close_instrument()

        coordinator._reconstruction_panel_logic.close_reconstruction.assert_called_once_with()

    def test_closing_with_no_instrument_draws_nothing(
        self,
        coordinator: ReconstructionTabCoordinator,
        views: List[ReconstructionInstrumentsViewModel],
    ) -> None:
        """A reconstruction the panel draws stays drawn, since the close reaches an instrument alone."""
        coordinator.close_instrument()

        assert views == []
        coordinator._reconstruction_panel_logic.close_reconstruction.assert_not_called()
