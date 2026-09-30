from pathlib import Path
from typing import Dict, Final, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.export import ExportMessages
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.tabs import reconstruction as reconstruction_module
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.instruments import (
    ReconstructionInstrumentsLogic,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.paths import LANG_EN
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import SILENT_VOLUME
from sampletones_core.exporters.skipped import NO_SKIPPED_ROWS
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.format import ExportFormat
from sampletones_core.features.envelope import Envelope
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
    LoadReconstructionError,
    UnhandledReconstructionError,
)
from sampletones_shared.types.callback import VoidCallback
from tests.suite.language import FakeLanguageManager
from tests.suite.sequencer import sample_reconstruction
from tests.suite.stems import RECORDED_SCALE, STEM_A_ID, STEM_B_ID, regenerated

FILE_NOT_FOUND_KEY: Final[str] = "reconstructions.browser.message.file_not_found"
LOAD_ERROR_KEY: Final[str] = "reconstructions.browser.message.load_error"
INVALID_METADATA_KEY: Final[str] = "global.dialog.message.invalid_metadata_error"
INVALID_VALUES_KEY: Final[str] = "reconstructions.browser.message.invalid_values"
INVALID_FILE_KEY: Final[str] = "reconstructions.browser.message.invalid_file"
DESERIALIZATION_ERROR_KEY: Final[str] = "reconstructions.browser.message.deserialization_error"
INCOMPATIBLE_VERSION_KEY: Final[str] = "reconstructions.browser.template.incompatible_version_template"
REMOVE_RECONSTRUCTION_MESSAGE_KEY: Final[str] = "reconstructions.browser.message.remove_reconstruction_message"
REMOVE_DIRECTORY_MESSAGE_KEY: Final[str] = "reconstructions.browser.message.remove_directory_message"

TEXTS: Final[Dict[str, str]] = {INCOMPATIBLE_VERSION_KEY: "got {} expected {}"}
HISTORY_BUDGET: Final[int] = 16
SHARED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
SOLE_CHANNEL: Final[ChannelName] = ChannelName.PULSE2
SHARED_OWNERS: Final[Tuple[int, ...]] = (STEM_A_ID, STEM_B_ID)
TYPED_VOLUME: Final[Tuple[int, ...]] = (6, 6)


@pytest.fixture
def coordinator() -> ReconstructionTabCoordinator:
    """A coordinator with only the collaborators ``load_reconstruction`` touches, bypassing the
    heavy constructor."""
    instance = object.__new__(ReconstructionTabCoordinator)
    instance._browser_panel = MagicMock()
    instance._reconstruction_manager = MagicMock()
    instance._dialogs = MagicMock()
    instance._language_manager = FakeLanguageManager(TEXTS)
    instance._msg_load_error = LOAD_ERROR_KEY
    return instance


class TestLoadReconstructionSurfacesConcreteErrors:
    """Each concrete load failure reaches the user through a populated error dialog, so a bad
    reconstruction file is reported rather than swallowed. The browser unlocks in every case.
    """

    @pytest.mark.parametrize(
        "error, expected_message",
        [
            (InvalidMetadataError("bad metadata"), INVALID_METADATA_KEY),
            (
                InvalidReconstructionValuesError("bad values", ValueError("v")),
                INVALID_VALUES_KEY,
            ),
            (InvalidReconstructionError("bad file"), INVALID_FILE_KEY),
            (DeserializationError("bad bytes"), DESERIALIZATION_ERROR_KEY),
            (LoadReconstructionError("unclassified"), LOAD_ERROR_KEY),
            (OSError("io"), LOAD_ERROR_KEY),
        ],
    )
    def test_concrete_error_shows_populated_dialog(
        self,
        coordinator: ReconstructionTabCoordinator,
        error: Exception,
        expected_message: str,
    ) -> None:
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error

        coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_called_once_with(
            error,
            expected_message,
        )
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_missing_file_shows_file_not_found_dialog(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        error = FileNotFoundError("gone")
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error
        path = Path("sample.stn")

        coordinator.load_reconstruction(path)

        coordinator._dialogs.show_file_not_found.assert_called_once_with(
            path,
            FILE_NOT_FOUND_KEY,
        )
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_incompatible_version_dialog_reports_both_versions(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        error = IncompatibleReconstructionVersionError(
            "mismatch",
            expected_version="2.0",
            actual_version="9.0",
        )
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error

        coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_called_once_with(error, "got 9.0 expected 2.0")
        coordinator._browser_panel.unlock.assert_called_once_with()


class TestLoadReconstructionTail:
    """The load pipeline wraps every unclassified deserialize failure in a
    ``LoadReconstructionError`` subtype, so the ladder's tail presents those with the generic
    load-error dialog; a failure outside the load contract is a bug and propagates. The browser
    unlocks either way."""

    def test_unclassified_load_error_shows_the_generic_dialog(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        error = UnhandledReconstructionError("wrapped")
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error

        coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_called_once_with(
            error,
            LOAD_ERROR_KEY,
        )
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_unexpected_error_propagates_and_unlocks(
        self,
        coordinator: ReconstructionTabCoordinator,
    ) -> None:
        coordinator._reconstruction_manager.load_reconstruction.side_effect = RuntimeError("bug")

        with pytest.raises(RuntimeError):
            coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_not_called()
        coordinator._browser_panel.unlock.assert_called_once_with()


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


@pytest.fixture
def removal_coordinator() -> ReconstructionTabCoordinator:
    instance = object.__new__(ReconstructionTabCoordinator)
    instance._dialogs = MagicMock()
    instance._browser_logic = MagicMock()
    instance._browser_panel = MagicMock()
    instance._reconstruction_manager = MagicMock()
    instance._language_manager = FakeLanguageManager(TEXTS)
    instance._lbl_remove = "Remove"
    instance._msg_load_error = LOAD_ERROR_KEY
    return instance


class TestRemoveTreeEntries:
    def test_request_remove_reconstruction_prompts_confirmation(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        path = Path("tone.strec")

        removal_coordinator._request_remove_reconstruction(path)

        confirmation = removal_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == REMOVE_RECONSTRUCTION_MESSAGE_KEY
        assert confirmation["path"] == path

        confirmation["on_confirm"]()
        removal_coordinator._browser_logic.remove_path.assert_called_once_with(path)

    def test_removing_open_reconstruction_detaches_and_marks_it_dirty(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        path = Path("tone.strec")
        removal_coordinator._reconstruction_manager.is_backed_by.return_value = True

        removal_coordinator._remove_reconstruction(path)

        removal_coordinator._reconstruction_manager.is_backed_by.assert_called_once_with(path)
        removal_coordinator._reconstruction_manager.detach_current_reconstruction.assert_called_once_with()
        removal_coordinator._reconstruction_manager.mark_updated.assert_called_once_with()
        removal_coordinator._browser_logic.remove_path.assert_called_once_with(path)
        removal_coordinator._browser_panel.refresh.assert_called_once_with()

    def test_removing_another_file_leaves_the_open_document_as_it_is(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        removal_coordinator._reconstruction_manager.is_backed_by.return_value = False

        removal_coordinator._remove_reconstruction(Path("other.strec"))

        removal_coordinator._reconstruction_manager.detach_current_reconstruction.assert_not_called()
        removal_coordinator._browser_logic.remove_path.assert_called_once_with(Path("other.strec"))

    def test_removing_open_directory_detaches_loaded_reconstruction_inside_it(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        directory = Path("set")
        removal_coordinator._reconstruction_manager.filepath = directory / "tone.strec"

        removal_coordinator._remove_directory(directory)

        removal_coordinator._reconstruction_manager.detach_current_reconstruction.assert_called_once_with()
        removal_coordinator._reconstruction_manager.mark_updated.assert_called_once_with()
        removal_coordinator._browser_logic.remove_path.assert_called_once_with(directory)
        removal_coordinator._browser_panel.refresh.assert_called_once_with()

    def test_request_remove_directory_prompts_with_path(
        self,
        removal_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        directory = Path("set")

        removal_coordinator._request_remove_directory(directory)

        confirmation = removal_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == REMOVE_DIRECTORY_MESSAGE_KEY
        assert confirmation["path"] == directory


@pytest.fixture
def export_coordinator(monkeypatch: pytest.MonkeyPatch) -> ReconstructionTabCoordinator:
    """A coordinator with only the collaborators ``_on_export_result`` touches.

    A report waits for the frame the export window leaves the screen in, so the wait is run
    through at once and what the coordinator reports stays observable from the call that asks.
    """

    def run_now(callback: VoidCallback, frame_count: int = 1) -> None:
        callback()

    monkeypatch.setattr(reconstruction_module.FrameCallbackManager, "set_frame_callback", run_now)

    instance = object.__new__(ReconstructionTabCoordinator)
    instance._dialogs = MagicMock()
    instance._export_messages = ExportMessages.build(LanguageManager(LANG_EN))
    return instance


def _shown_message(coordinator: ReconstructionTabCoordinator) -> str:
    _, message, _ = coordinator._dialogs.show_message_with_path.call_args.args
    return message


class TestExportingTheInstrumentInFront:
    """Whatever the tab holds reaches a file the same way, so a pool voice is written by voice."""

    @staticmethod
    def _coordinator(
        instrument: object,
        exportable: object,
    ) -> ReconstructionTabCoordinator:
        instance = object.__new__(ReconstructionTabCoordinator)
        instance._instrument_editor = MagicMock()
        instance._instrument_editor.instrument = instrument
        instance._instrument_exports = MagicMock()
        instance._reconstruction_panel_logic = MagicMock()
        instance._reconstruction_panel_logic.exportable_instrument.return_value = exportable
        return instance

    def test_a_hand_written_voice_is_written_by_the_voice_it_is(self) -> None:
        """The sequencer's menu and this button name the same voice, so they write the same file."""
        instrument = MagicMock()
        instrument.id = "lead-id"
        coordinator = self._coordinator(instrument, MagicMock())

        coordinator._export_instrument(ChannelName.PULSE1)

        coordinator._instrument_exports.request_voice.assert_called_once_with("lead-id", None)
        coordinator._reconstruction_panel_logic.exportable_instrument.assert_not_called()

    def test_a_reconstructions_slice_is_written_as_the_tab_holds_it(self) -> None:
        exportable = MagicMock()
        coordinator = self._coordinator(None, exportable)

        coordinator._export_instrument(ChannelName.TRIANGLE)

        coordinator._instrument_exports.request.assert_called_once_with(
            exportable.source,
            exportable.name,
        )

    def test_a_channel_describing_no_frame_is_written_nowhere(self) -> None:
        coordinator = self._coordinator(None, None)

        coordinator._export_instrument(ChannelName.NOISE)

        coordinator._instrument_exports.request.assert_not_called()


class TestExportResultReportsTruncation:
    def test_a_complete_instrument_export_shows_the_success_message(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.INSTRUMENT,
                filepath=Path("lead.fti"),
                export_format=ExportFormat.FAMITRACKER,
                truncation=None,
                skipped_rows=NO_SKIPPED_ROWS,
            )
        )

        assert _shown_message(export_coordinator) == export_coordinator._export_messages.instrument_success

    def test_a_shortened_instrument_export_names_both_frame_counts(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.INSTRUMENT,
                filepath=Path("lead.fti"),
                export_format=ExportFormat.FAMITRACKER,
                truncation=EnvelopeTruncation(frames=252, source_frames=300, instruments=1),
                skipped_rows=NO_SKIPPED_ROWS,
            )
        )

        message = _shown_message(export_coordinator)
        assert export_coordinator._export_messages.instrument_success in message
        assert "300" in message
        assert "252" in message

    def test_a_shortened_reconstruction_export_counts_the_instruments(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.SAMPLE,
                filepath=Path("instruments"),
                export_format=ExportFormat.FAMITRACKER,
                truncation=EnvelopeTruncation(
                    frames=252,
                    source_frames=410,
                    instruments=3,
                ),
                skipped_rows=NO_SKIPPED_ROWS,
            )
        )

        message = _shown_message(export_coordinator)
        assert export_coordinator._export_messages.instruments_success in message
        assert "3" in message

    def test_a_wav_export_shows_its_own_message(
        self,
        export_coordinator: ReconstructionTabCoordinator,
    ) -> None:
        export_coordinator._on_export_result(
            ExportSuccess(
                kind=ExportKind.WAV,
                filepath=Path("track.wav"),
                export_format=None,
                truncation=None,
                skipped_rows=NO_SKIPPED_ROWS,
            )
        )

        assert _shown_message(export_coordinator) == export_coordinator._export_messages.wav_success


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

        coordinator.redraw_reconstruction()

        coordinator._reconstruction_panel_logic.update_reconstruction.assert_called_once_with(refit_waveform=False)


class TestTheInstrumentsPanelDrawsTheDocument:
    """A document rewritten outside the instruments panel is drawn as it stands, and one the panel's
    own edit rebuilt keeps the envelopes the panel draws."""

    @pytest.fixture
    def reconstruction(self, tmp_path: Path) -> Reconstruction:
        """Two recordings taking turns on the shared channel, the second holding the sole channel alone."""
        base = sample_reconstruction([SHARED_CHANNEL, SOLE_CHANNEL])
        streams = dict(base.streams)
        streams[SHARED_CHANNEL] = InstructionsItem.create(
            channel_name=SHARED_CHANNEL,
            instructions=base.instructions[SHARED_CHANNEL] * len(SHARED_OWNERS),
            initial_pitch=base.initial_pitches[SHARED_CHANNEL],
            held_features=base.held_features[SHARED_CHANNEL],
        )
        stems_data = StemsData(
            config=StemsConfig(
                entries=[
                    StemEntry(id=STEM_A_ID, settings=StemSettings.covering([SHARED_CHANNEL])),
                    StemEntry(id=STEM_B_ID, settings=StemSettings.covering([SHARED_CHANNEL, SOLE_CHANNEL])),
                ],
                hierarchy=StemsHierarchy(levels=[[STEM_A_ID, STEM_B_ID]]),
            ),
            assignments=[
                ChannelAssignment(channel_name=SHARED_CHANNEL, stem_ids=list(SHARED_OWNERS)),
                ChannelAssignment(channel_name=SOLE_CHANNEL, stem_ids=[STEM_B_ID]),
            ],
            scale=RECORDED_SCALE,
        ).with_sources((tmp_path / "a.wav", tmp_path / "b.wav"))
        return base.rewritten(streams, stems_data)

    @pytest.fixture
    def reconstruction_manager(
        self,
        reconstruction: Reconstruction,
        scheduling: SchedulingBehavior,
    ) -> ReconstructionManager:
        manager = ReconstructionManager(scheduling=scheduling)
        manager.load_reconstruction_object(reconstruction, name="lead")
        return manager

    @pytest.fixture
    def instruments_logic(
        self,
        reconstruction_manager: ReconstructionManager,
        scheduling: SchedulingBehavior,
    ) -> ReconstructionInstrumentsLogic:
        """The panel's logic over the editor the application builds, reading the open document."""
        controller = ProjectController(ProjectManager())
        editor = InstrumentEditor(
            reconstruction_manager,
            controller,
            HistoryManager(controller, budget=HISTORY_BUDGET, strict=True),
            lambda _voice_id, _feature_key: (),
        )
        return ReconstructionInstrumentsLogic(editor, scheduling=scheduling)

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

    def test_a_removal_draws_the_document_it_leaves(
        self,
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
        drawn: List[Optional[ChannelEnvelopesViewModel]],
    ) -> None:
        reconstruction_manager.apply_edited(without_stem(reconstruction, STEM_B_ID))

        coordinator.redraw_reconstruction()

        assert drawn == [reconstruction_manager.current_features]

    def test_a_removal_draws_the_frames_it_released_as_rests(
        self,
        coordinator: ReconstructionTabCoordinator,
        reconstruction_manager: ReconstructionManager,
        reconstruction: Reconstruction,
        drawn: List[Optional[ChannelEnvelopesViewModel]],
    ) -> None:
        reconstruction_manager.apply_edited(without_stem(reconstruction, STEM_B_ID))

        coordinator.redraw_reconstruction()

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
        reconstruction_manager.apply_edited(without_stem(reconstruction, STEM_B_ID))

        coordinator.redraw_reconstruction()

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
        reconstruction_manager.apply_edited(regenerated(reconstruction, SHARED_CHANNEL, typed))

        coordinator.update_reconstruction()

        assert drawn == []
