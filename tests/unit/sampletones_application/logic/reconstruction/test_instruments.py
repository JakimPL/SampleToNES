from typing import Callable, Dict, Final, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.envelopes import heard_envelopes
from sampletones_application.logic.reconstruction.instruments import (
    ReconstructionInstrumentsLogic,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.queue import ReconstructionRewrites
from sampletones_application.logic.reconstruction.rewrites.steps import ChannelChange
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.footprint import (
    features_footprint,
    reconstruction_footprints,
    total_footprint,
)
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.reconstructions import Reconstruction
from tests.suite.application import HeldQueue, held_queue
from tests.suite.regeneration import HeldRegeneration
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, everything_heard, regenerated, taking_turns

__all__ = ["held_queue", "taking_turns"]


def _heard_features(reconstruction: Reconstruction) -> ChannelEnvelopesViewModel:
    """The envelopes of the whole document, which is what a fresh reader hears."""
    return heard_envelopes(reconstruction, everything_heard(reconstruction))


HISTORY_BUDGET: Final[int] = 16
NEW_PITCH: Final[int] = 61
SILENCED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


def _silent_volume(features: Features) -> Envelope[int]:
    """A volume quieting every frame the envelopes describe."""
    return Envelope[int](items=(0,) * features.frame_count)


def _editor(
    reconstruction_manager: MagicMock,
    controller: ProjectController,
) -> InstrumentEditor:
    """The editor over a strict history, which is how the application builds it."""
    return InstrumentEditor(
        reconstruction_manager,
        controller,
        HistoryManager(controller, budget=HISTORY_BUDGET, strict=True),
        lambda _voice_id, _feature_key: (),
    )


@pytest.fixture
def mock_reconstruction_manager() -> MagicMock:
    return MagicMock(spec=ReconstructionManager)


@pytest.fixture
def instrument_editor(mock_reconstruction_manager: MagicMock) -> InstrumentEditor:
    """The real source the panel reads, over a stand-in for the document it opens."""
    return _editor(mock_reconstruction_manager, ProjectController(ProjectManager()))


@pytest.fixture
def regeneration() -> HeldRegeneration:
    return HeldRegeneration()


@pytest.fixture
def rewrites(
    mock_reconstruction_manager: MagicMock,
    regeneration: HeldRegeneration,
) -> ReconstructionRewrites:
    """The steps of the open document, each rebuild held until a case lands it."""
    return ReconstructionRewrites(mock_reconstruction_manager, regeneration)


def _logic(editor: InstrumentEditor, rewrites: ReconstructionRewrites) -> ReconstructionInstrumentsLogic:
    """The panel's logic, sending every change on to the document's steps the way the tab wires it."""
    logic = ReconstructionInstrumentsLogic(editor, rewrites)
    logic.on_channel_changed = rewrites.request
    return logic


@pytest.fixture
def instruments_logic(
    instrument_editor: InstrumentEditor,
    rewrites: ReconstructionRewrites,
) -> ReconstructionInstrumentsLogic:
    return _logic(instrument_editor, rewrites)


class TestReconstructionInstrumentsLogicUpdateDisplay:
    def test_no_features_emits_not_loaded_view_model(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append
        instruments_logic.update_display()
        assert len(received) == 1
        assert received[0].reconstruction_loaded is False

    def test_no_features_fires_on_feature_data_changed_with_none(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        received: List[Optional[Dict[ChannelName, Features]]] = []
        instruments_logic.on_feature_data_changed = received.append
        instruments_logic.update_display()
        assert received == [None]

    def test_with_features_emits_loaded_view_model(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append
        instruments_logic.update_display()
        assert received[0].reconstruction_loaded is True

    def test_with_features_fires_on_feature_data_changed_with_data(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        feature_data = _heard_features(reconstruction_factory())
        mock_reconstruction_manager.current_features = feature_data
        received: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = received.append
        instruments_logic.update_display()
        assert received == [ChannelEnvelopesViewModel(channels=feature_data.channels, ownership=feature_data.ownership)]

    def test_with_features_exposes_the_playing_generators(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append
        instruments_logic.update_display()
        assert ChannelName.PULSE1 in received[0].playing_channels


class TestReconstructionInstrumentsLogicFootprint:
    """The byte figures the view carries, measured from the envelopes the manager holds."""

    def test_no_reconstruction_carries_no_footprint(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        mock_reconstruction_manager.current_features = None
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append
        instruments_logic.update_display()
        assert received[0].footprint is None

    def test_every_playing_channel_is_measured(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        feature_data = _heard_features(reconstruction_factory())
        mock_reconstruction_manager.current_features = feature_data
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append
        instruments_logic.update_display()
        footprint = received[0].footprint
        assert footprint is not None
        assert {instrument.channel for instrument in footprint.instruments} == {
            channel_name for channel_name, features in feature_data.channels.items() if features.has_frames
        }

    def test_the_size_is_the_one_a_one_shot_export_writes(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """A reconstruction exports its instruments as one-shots, so that is the size shown."""
        feature_data = _heard_features(reconstruction_factory())
        mock_reconstruction_manager.current_features = feature_data
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append
        instruments_logic.update_display()
        footprint = received[0].footprint
        assert footprint is not None
        expected = total_footprint(
            features_footprint(features) for features in feature_data.channels.values() if features.has_frames
        )
        assert footprint.total_bytes == expected.total_bytes

    def test_an_envelope_edit_is_measured_as_it_arrives(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """The typed envelope is measured at once, so the figure answers what is on screen."""
        feature_data = _heard_features(reconstruction_factory())
        mock_reconstruction_manager.current_features = feature_data
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append

        volume = Envelope[int](items=(15, 12, 8, 4, 0))
        instruments_logic.handle_envelope_changed(
            ChannelName.PULSE1,
            FeatureKey.VOLUME,
            volume,
        )

        edited = feature_data.channels[ChannelName.PULSE1].with_envelope(FeatureKey.VOLUME, volume)
        footprint = received[0].footprint
        assert footprint is not None
        assert footprint.bytes_for(ChannelName.PULSE1) == features_footprint(edited).total_bytes

    def test_measuring_an_edit_leaves_the_loaded_envelopes_as_they_are(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """The regeneration owns the loaded envelopes, so the measurement reads them without writing."""
        feature_data = _heard_features(reconstruction_factory())
        mock_reconstruction_manager.current_features = feature_data
        loaded_volume = feature_data.channels[ChannelName.PULSE1].volume

        instruments_logic.handle_envelope_changed(
            ChannelName.PULSE1,
            FeatureKey.VOLUME,
            Envelope[int](items=(15, 12, 8, 4, 0)),
        )

        assert feature_data.channels[ChannelName.PULSE1].volume == loaded_volume

    def test_a_refresh_reports_the_view_alone(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """A regenerated reconstruction refreshes the figures, leaving the edited envelopes displayed."""
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        received: List[ReconstructionInstrumentsViewModel] = []
        feature_updates: List[Optional[Dict[ChannelName, Features]]] = []
        instruments_logic.on_view_changed = received.append
        instruments_logic.on_feature_data_changed = feature_updates.append

        instruments_logic.refresh_view()

        assert len(received) == 1
        assert received[0].footprint is not None
        assert feature_updates == []


class TestAnEditSilencingAChannel:
    """A channel an edit writes silent stands by in the document, and the panel says so too."""

    @pytest.fixture
    def reconstruction(self, reconstruction_factory: Callable[[], Reconstruction]) -> Reconstruction:
        return reconstruction_factory()

    @pytest.fixture
    def silenced(self, reconstruction: Reconstruction) -> Features:
        """The first pulse's envelopes with every frame's volume at nothing."""
        features = _heard_features(reconstruction)[SILENCED_CHANNEL]
        return features.with_envelope(FeatureKey.VOLUME, _silent_volume(features))

    def test_an_edit_writing_every_frame_silent_is_measured_standing_by(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction: Reconstruction,
        silenced: Features,
    ) -> None:
        """The figure the edit shows at once is the one the regenerated document reports."""
        mock_reconstruction_manager.current_features = _heard_features(reconstruction)
        received: List[ReconstructionInstrumentsViewModel] = []
        instruments_logic.on_view_changed = received.append

        instruments_logic.handle_envelope_changed(SILENCED_CHANNEL, FeatureKey.VOLUME, silenced.volume)

        landed = regenerated(reconstruction, SILENCED_CHANNEL, silenced)
        footprint = received[0].footprint
        assert footprint is not None
        assert SILENCED_CHANNEL not in received[0].playing_channels
        assert footprint.bytes_for(SILENCED_CHANNEL) is None
        assert footprint.total_bytes == total_footprint(reconstruction_footprints(landed).values()).total_bytes

    def test_an_edit_standing_a_channel_by_redraws_it_empty(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        regeneration: HeldRegeneration,
        mock_reconstruction_manager: MagicMock,
        reconstruction: Reconstruction,
        silenced: Features,
    ) -> None:
        """Once the regeneration lands, the panel draws what the document holds for that channel."""
        mock_reconstruction_manager.current_features = _heard_features(reconstruction)
        feature_updates: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = feature_updates.append
        instruments_logic.handle_envelope_changed(SILENCED_CHANNEL, FeatureKey.VOLUME, silenced.volume)

        rebuilt = regenerated(reconstruction, SILENCED_CHANNEL, silenced)
        regeneration.finish_with(rebuilt)
        landed = _heard_features(rebuilt)
        mock_reconstruction_manager.current_features = landed
        instruments_logic.refresh_view()

        assert feature_updates == [
            ChannelEnvelopesViewModel(channels={SILENCED_CHANNEL: landed[SILENCED_CHANNEL]}, ownership={})
        ]
        assert not landed[SILENCED_CHANNEL].has_frames

    def test_the_channel_is_redrawn_once(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        regeneration: HeldRegeneration,
        mock_reconstruction_manager: MagicMock,
        reconstruction: Reconstruction,
        silenced: Features,
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction)
        feature_updates: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = feature_updates.append
        instruments_logic.handle_envelope_changed(SILENCED_CHANNEL, FeatureKey.VOLUME, silenced.volume)
        rebuilt = regenerated(reconstruction, SILENCED_CHANNEL, silenced)
        regeneration.finish_with(rebuilt)
        mock_reconstruction_manager.current_features = _heard_features(rebuilt)

        instruments_logic.refresh_view()
        instruments_logic.refresh_view()

        assert len(feature_updates) == 1

    def test_an_edit_that_sounds_again_before_it_lands_leaves_the_envelopes_displayed(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        regeneration: HeldRegeneration,
        mock_reconstruction_manager: MagicMock,
        reconstruction: Reconstruction,
        silenced: Features,
    ) -> None:
        """The latest edit decides, so a channel written back into play keeps what the reader drew."""
        features = _heard_features(reconstruction)
        mock_reconstruction_manager.current_features = features
        feature_updates: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = feature_updates.append
        instruments_logic.handle_envelope_changed(SILENCED_CHANNEL, FeatureKey.VOLUME, silenced.volume)
        instruments_logic.handle_envelope_changed(
            SILENCED_CHANNEL,
            FeatureKey.VOLUME,
            features[SILENCED_CHANNEL].volume,
        )
        rebuilt = regenerated(reconstruction, SILENCED_CHANNEL, silenced)
        regeneration.finish_with(rebuilt)
        mock_reconstruction_manager.current_features = _heard_features(rebuilt)

        instruments_logic.refresh_view()

        assert feature_updates == []


class TestReconstructionInstrumentsLogicHandlePitchValueChanged:
    def test_a_moved_pitch_travels_on_as_a_change(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        callback = MagicMock()
        instruments_logic.on_channel_changed = callback
        instruments_logic.handle_pitch_value_changed(ChannelName.PULSE1, NEW_PITCH)
        callback.assert_called_once()

    def test_the_change_carries_the_channel_and_the_pitch_alone(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        received: List[ChannelChange] = []
        instruments_logic.on_channel_changed = received.append

        instruments_logic.handle_pitch_value_changed(ChannelName.PULSE1, NEW_PITCH)

        (change,) = received
        assert change.channel_name == ChannelName.PULSE1
        assert change.feature_key == FeatureKey.INITIAL_PITCH
        assert change.initial_pitch == NEW_PITCH
        assert change.envelopes == {}


class TestReconstructionInstrumentsLogicHandleEnvelope:
    def test_an_edited_envelope_travels_on_as_a_change(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        callback = MagicMock()
        instruments_logic.on_channel_changed = callback
        instruments_logic.handle_envelope_changed(
            ChannelName.PULSE1,
            FeatureKey.VOLUME,
            Envelope[int](items=(0, 0, 0, 0)),
        )
        callback.assert_called_once()

    def test_an_edited_envelope_keeps_the_point_it_was_given(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """The panel states values and loop point together, so the change carries both."""
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        received: List[ChannelChange] = []
        instruments_logic.on_channel_changed = received.append
        arpeggio = Envelope[int](items=(0, 4, 7), loop_point=1)

        instruments_logic.handle_envelope_changed(
            ChannelName.PULSE1,
            FeatureKey.ARPEGGIO,
            arpeggio,
        )

        assert received[0].envelopes == {FeatureKey.ARPEGGIO: arpeggio}

    def test_the_change_carries_the_dimension_moved_alone(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """The rest of the channel is read at the change's turn, so a step before it stands."""
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        received: List[ChannelChange] = []
        instruments_logic.on_channel_changed = received.append

        instruments_logic.handle_envelope_changed(ChannelName.PULSE1, FeatureKey.VOLUME, Envelope[int](items=(7,)))

        (change,) = received
        assert change.feature_key == FeatureKey.VOLUME
        assert list(change.envelopes) == [FeatureKey.VOLUME]
        assert change.initial_pitch is None


class TestTheInstrumentsPanelShowsAnInstrument:
    """An instrument stands on no audio, so the panel shows one instrument and writes edits at once."""

    @pytest.fixture
    def project_controller(self) -> ProjectController:
        return ProjectController(ProjectManager())

    @pytest.fixture
    def instrument_logic(
        self,
        mock_reconstruction_manager: MagicMock,
        project_controller: ProjectController,
        rewrites: ReconstructionRewrites,
    ) -> ReconstructionInstrumentsLogic:
        mock_reconstruction_manager.current_features = None
        editor = _editor(mock_reconstruction_manager, project_controller)
        instrument = project_controller.add_instrument(new_instrument("lead"))
        project_controller.set_instrument_envelope(instrument.id, FeatureKey.VOLUME, Envelope(items=(15, 12)))
        editor.edit_instrument(instrument.id)
        return _logic(editor, rewrites)

    def test_the_view_names_the_instrument_it_shows(
        self,
        instrument_logic: ReconstructionInstrumentsLogic,
    ) -> None:
        received: List[ReconstructionInstrumentsViewModel] = []
        instrument_logic.on_view_changed = received.append

        instrument_logic.update_display()

        assert received[-1].edits_an_instrument is True
        assert received[-1].instrument is not None
        assert received[-1].instrument.name == "lead"

    def test_the_tab_it_is_shown_under_plays_it(
        self,
        instrument_logic: ReconstructionInstrumentsLogic,
    ) -> None:
        """The tab that plays is the tab an export is offered from, so the button is reachable."""
        received: List[ReconstructionInstrumentsViewModel] = []
        instrument_logic.on_view_changed = received.append

        instrument_logic.update_display()

        assert received[-1].playing_channels == frozenset({INSTRUMENT_CHANNEL})

    def test_an_instrument_with_nothing_written_stands_by(
        self,
        instrument_logic: ReconstructionInstrumentsLogic,
        project_controller: ProjectController,
    ) -> None:
        """An export writes what has frames, so a voice holding none is offered no export."""
        instrument = project_controller.project.voices[0]
        project_controller.set_instrument_envelope(instrument.id, FeatureKey.VOLUME, Envelope(items=()))
        received: List[ReconstructionInstrumentsViewModel] = []
        instrument_logic.on_view_changed = received.append

        instrument_logic.update_display()

        assert received[-1].playing_channels == frozenset()

    def test_the_envelopes_are_drawn_under_the_channel_that_reads_them_all(
        self,
        instrument_logic: ReconstructionInstrumentsLogic,
    ) -> None:
        received: List[Optional[ChannelEnvelopesViewModel]] = []
        instrument_logic.on_feature_data_changed = received.append

        instrument_logic.update_display()

        envelopes = received[-1]
        assert envelopes is not None
        assert list(envelopes.channels) == [INSTRUMENT_CHANNEL]
        assert envelopes.ownership == {}

    def test_an_envelope_edit_reaches_the_instrument_without_a_regeneration(
        self,
        instrument_logic: ReconstructionInstrumentsLogic,
        project_controller: ProjectController,
    ) -> None:
        regenerated: List[object] = []
        instrument_logic.on_channel_changed = regenerated.append

        instrument_logic.handle_envelope_changed(
            INSTRUMENT_CHANNEL,
            FeatureKey.ARPEGGIO,
            Envelope[int](items=(0, 7)),
        )

        instrument = project_controller.project.voices[project_controller.project.voices[0].id]
        assert instrument.envelopes.arpeggio.items == (0, 7)
        assert regenerated == []

    def test_the_figure_measures_the_one_instrument_it_exports(
        self,
        instrument_logic: ReconstructionInstrumentsLogic,
        project_controller: ProjectController,
    ) -> None:
        received: List[ReconstructionInstrumentsViewModel] = []
        instrument_logic.on_view_changed = received.append

        instrument_logic.update_display()

        instrument = project_controller.project.voices[0]
        assert received[-1].footprint is not None
        assert received[-1].footprint.total_bytes == features_footprint(instrument.instrument_features()).total_bytes


class TestAnEditReachingAVoiceThatLeft:
    """A gesture the panel sent before its voice left draws the panel as it now stands and goes nowhere."""

    @pytest.fixture
    def project_controller(self) -> ProjectController:
        return ProjectController(ProjectManager())

    @pytest.fixture
    def left_logic(
        self,
        mock_reconstruction_manager: MagicMock,
        project_controller: ProjectController,
        rewrites: ReconstructionRewrites,
    ) -> ReconstructionInstrumentsLogic:
        """The panel's logic over an instrument the project has since removed."""
        mock_reconstruction_manager.current_features = None
        editor = _editor(mock_reconstruction_manager, project_controller)
        instrument = project_controller.add_instrument(new_instrument("lead"))
        editor.edit_instrument(instrument.id)
        project_controller.remove_voice(instrument.id)
        return _logic(editor, rewrites)

    def test_an_envelope_edit_draws_the_panel_empty(
        self,
        left_logic: ReconstructionInstrumentsLogic,
    ) -> None:
        views: List[ReconstructionInstrumentsViewModel] = []
        left_logic.on_view_changed = views.append

        left_logic.handle_envelope_changed(INSTRUMENT_CHANNEL, FeatureKey.VOLUME, Envelope[int](items=(7,)))

        assert len(views) == 1
        assert views[0].instrument is None
        assert not views[0].reconstruction_loaded

    def test_an_envelope_edit_goes_nowhere(
        self,
        left_logic: ReconstructionInstrumentsLogic,
    ) -> None:
        regenerated: List[object] = []
        left_logic.on_channel_changed = regenerated.append

        left_logic.handle_envelope_changed(INSTRUMENT_CHANNEL, FeatureKey.VOLUME, Envelope[int](items=(7,)))

        assert regenerated == []

    def test_a_pitch_change_draws_the_panel_empty(
        self,
        left_logic: ReconstructionInstrumentsLogic,
    ) -> None:
        views: List[ReconstructionInstrumentsViewModel] = []
        left_logic.on_view_changed = views.append
        regenerated: List[object] = []
        left_logic.on_channel_changed = regenerated.append

        left_logic.handle_pitch_value_changed(ChannelName.PULSE1, NEW_PITCH)

        assert len(views) == 1
        assert views[0].instrument is None
        assert regenerated == []

    def test_an_envelope_edit_after_the_document_closed_goes_nowhere(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
    ) -> None:
        """A close lands on the panel a moment later, so an edit can reach it in between."""
        mock_reconstruction_manager.current_features = None
        received: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = received.append
        regenerated: List[object] = []
        instruments_logic.on_channel_changed = regenerated.append

        instruments_logic.handle_envelope_changed(ChannelName.PULSE1, FeatureKey.VOLUME, Envelope[int](items=(7,)))

        assert received == [None]
        assert regenerated == []

    def test_a_pitch_change_reaching_an_instrument_goes_nowhere(
        self,
        mock_reconstruction_manager: MagicMock,
        project_controller: ProjectController,
        rewrites: ReconstructionRewrites,
    ) -> None:
        """The panel offers the pitch on a reconstruction's channels alone."""
        mock_reconstruction_manager.current_features = None
        editor = _editor(mock_reconstruction_manager, project_controller)
        editor.edit_instrument(project_controller.add_instrument(new_instrument("lead")).id)
        logic = _logic(editor, rewrites)
        views: List[ReconstructionInstrumentsViewModel] = []
        logic.on_view_changed = views.append
        regenerated: List[object] = []
        logic.on_channel_changed = regenerated.append

        logic.handle_pitch_value_changed(INSTRUMENT_CHANNEL, NEW_PITCH)

        assert regenerated == []
        assert len(views) == 1
        assert views[0].instrument is not None


class TestEveryGestureReachesTheDocument:
    """Each gesture the panel makes travels on to the document, however quickly the next one follows."""

    def test_two_channels_edited_within_one_frame_both_reach_the_document(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        held_queue: HeldQueue,
        taking_turns: Reconstruction,
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(taking_turns)
        reached: List[ChannelName] = []
        instruments_logic.on_channel_changed = lambda change: reached.append(change.channel_name)

        instruments_logic.handle_envelope_changed(SHARED_CHANNEL, FeatureKey.VOLUME, Envelope[int](items=(5, 5)))
        instruments_logic.handle_envelope_changed(SOLE_CHANNEL, FeatureKey.VOLUME, Envelope[int](items=(3,)))
        held_queue.drain()

        assert reached == [SHARED_CHANNEL, SOLE_CHANNEL]

    def test_a_change_waiting_behind_a_rebuild_is_measured(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        taking_turns: Reconstruction,
    ) -> None:
        """The figures answer for what the document will hold, a change still waiting included."""
        mock_reconstruction_manager.current_features = _heard_features(taking_turns)
        views: List[ReconstructionInstrumentsViewModel] = []
        sole = Envelope[int](items=(3, 3, 3))
        instruments_logic.handle_envelope_changed(SHARED_CHANNEL, FeatureKey.VOLUME, Envelope[int](items=(5, 5)))
        instruments_logic.handle_envelope_changed(SOLE_CHANNEL, FeatureKey.VOLUME, sole)
        instruments_logic.on_view_changed = views.append

        instruments_logic.refresh_view()

        edited = _heard_features(taking_turns)[SOLE_CHANNEL].with_envelope(FeatureKey.VOLUME, sole)
        footprint = views[-1].footprint
        assert footprint is not None
        assert footprint.bytes_for(SOLE_CHANNEL) == features_footprint(edited).total_bytes

    def test_a_redraw_draws_the_changes_on_their_way(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        taking_turns: Reconstruction,
    ) -> None:
        """A redraw while a change waits draws the change, so the bars the reader moved stay where they left them."""
        mock_reconstruction_manager.current_features = _heard_features(taking_turns)
        shared = Envelope[int](items=(5, 5))
        sole = Envelope[int](items=(3,))
        instruments_logic.handle_envelope_changed(SHARED_CHANNEL, FeatureKey.VOLUME, shared)
        instruments_logic.handle_envelope_changed(SOLE_CHANNEL, FeatureKey.VOLUME, sole)
        drawn: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = drawn.append

        instruments_logic.update_display()

        envelopes = drawn[-1]
        assert envelopes is not None
        assert envelopes[SHARED_CHANNEL].volume == shared
        assert envelopes[SOLE_CHANNEL].volume == sole
