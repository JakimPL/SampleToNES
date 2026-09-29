from typing import Callable, Dict, Final, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.constants.instruments import INSTRUMENT_CHANNEL
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.editor import InstrumentEditor
from sampletones_application.logic.reconstruction.envelopes import heard_envelopes
from sampletones_application.logic.reconstruction.instruments import (
    ReconstructionInstrumentsLogic,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP, Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.footprint import (
    features_footprint,
    reconstruction_footprints,
    total_footprint,
)
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.reconstructions import Reconstruction
from tests.suite.stems import everything_heard


def _heard_features(reconstruction: Reconstruction) -> ChannelEnvelopesViewModel:
    """The envelopes of the whole document, which is what a fresh reader hears."""
    return heard_envelopes(reconstruction, everything_heard(reconstruction))


HISTORY_BUDGET: Final[int] = 16
NEW_PITCH: Final[int] = 61
SILENCED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


def _silent_volume(features: Features) -> Envelope[int]:
    """A volume quieting every frame the envelopes describe."""
    return Envelope[int](items=(0,) * features.frame_count)


def _regenerated(reconstruction: Reconstruction, channel_name: ChannelName, features: Features) -> Reconstruction:
    """The document a regeneration leaves once it rebuilds one channel from ``features``."""
    regenerated = reconstruction.model_copy(deep=True)
    regenerated.update_channel_data(
        channel_name,
        list(CHANNEL_TO_EXPORTER_MAP[channel_name].from_features(features)),
        features.initial_pitch,
        features.held_features,
        heard=regenerated.recorded_stem_ids,
    )
    return regenerated


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
def instruments_logic(
    instrument_editor: InstrumentEditor,
    scheduling: SchedulingBehavior,
) -> ReconstructionInstrumentsLogic:
    return ReconstructionInstrumentsLogic(
        instrument_editor,
        scheduling=scheduling,
    )


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

        regenerated = _regenerated(reconstruction, SILENCED_CHANNEL, silenced)
        footprint = received[0].footprint
        assert footprint is not None
        assert SILENCED_CHANNEL not in received[0].playing_channels
        assert footprint.bytes_for(SILENCED_CHANNEL) is None
        assert footprint.total_bytes == total_footprint(reconstruction_footprints(regenerated).values()).total_bytes

    def test_an_edit_standing_a_channel_by_redraws_it_empty(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction: Reconstruction,
        silenced: Features,
    ) -> None:
        """Once the regeneration lands, the panel draws what the document holds for that channel."""
        mock_reconstruction_manager.current_features = _heard_features(reconstruction)
        feature_updates: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = feature_updates.append
        instruments_logic.handle_envelope_changed(SILENCED_CHANNEL, FeatureKey.VOLUME, silenced.volume)

        landed = _heard_features(_regenerated(reconstruction, SILENCED_CHANNEL, silenced))
        mock_reconstruction_manager.current_features = landed
        instruments_logic.refresh_view()

        assert feature_updates == [
            ChannelEnvelopesViewModel(channels={SILENCED_CHANNEL: landed[SILENCED_CHANNEL]}, ownership={})
        ]
        assert not landed[SILENCED_CHANNEL].has_frames

    def test_the_channel_is_redrawn_once(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction: Reconstruction,
        silenced: Features,
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction)
        feature_updates: List[Optional[ChannelEnvelopesViewModel]] = []
        instruments_logic.on_feature_data_changed = feature_updates.append
        instruments_logic.handle_envelope_changed(SILENCED_CHANNEL, FeatureKey.VOLUME, silenced.volume)
        mock_reconstruction_manager.current_features = _heard_features(
            _regenerated(reconstruction, SILENCED_CHANNEL, silenced)
        )

        instruments_logic.refresh_view()
        instruments_logic.refresh_view()

        assert len(feature_updates) == 1

    def test_an_edit_that_sounds_again_before_it_lands_leaves_the_envelopes_displayed(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
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
        mock_reconstruction_manager.current_features = _heard_features(
            _regenerated(reconstruction, SILENCED_CHANNEL, silenced)
        )

        instruments_logic.refresh_view()

        assert feature_updates == []


class TestReconstructionInstrumentsLogicHandlePitchValueChanged:
    def test_schedules_reconstruction_update(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        callback = MagicMock()
        instruments_logic.on_reconstruction_instrument_updated = callback
        instruments_logic.handle_pitch_value_changed(ChannelName.PULSE1, NEW_PITCH)
        callback.assert_called_once()

    def test_forwards_generator_pitch_feature_and_value(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        callback = MagicMock()
        instruments_logic.on_reconstruction_instrument_updated = callback

        instruments_logic.handle_pitch_value_changed(ChannelName.PULSE1, NEW_PITCH)

        channel_name, feature_key, features = callback.call_args.args
        assert channel_name == ChannelName.PULSE1
        assert feature_key == FeatureKey.INITIAL_PITCH
        assert features.initial_pitch == NEW_PITCH


class TestReconstructionInstrumentsLogicHandleEnvelope:
    def test_an_edited_envelope_schedules_an_update(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
        mock_reconstruction_manager: MagicMock,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        callback = MagicMock()
        instruments_logic.on_reconstruction_instrument_updated = callback
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
        """The panel states values and loop point together, so the update carries both."""
        mock_reconstruction_manager.current_features = _heard_features(reconstruction_factory())
        received: List[Features] = []
        instruments_logic.on_reconstruction_instrument_updated = lambda _channel, _key, features: received.append(
            features
        )
        arpeggio = Envelope[int](items=(0, 4, 7), loop_point=1)

        instruments_logic.handle_envelope_changed(
            ChannelName.PULSE1,
            FeatureKey.ARPEGGIO,
            arpeggio,
        )

        assert received[0].arpeggio == arpeggio


class TestReconstructionInstrumentsLogicOnUpdateScheduled:
    def test_no_pending_update_is_a_no_op(
        self,
        instruments_logic: ReconstructionInstrumentsLogic,
    ) -> None:
        callback = MagicMock()
        instruments_logic.on_reconstruction_instrument_updated = callback
        instruments_logic._pending_reconstruction_update = None
        instruments_logic._on_reconstruction_update_scheduled()
        callback.assert_not_called()


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
        scheduling: SchedulingBehavior,
    ) -> ReconstructionInstrumentsLogic:
        mock_reconstruction_manager.current_features = None
        editor = _editor(mock_reconstruction_manager, project_controller)
        instrument = project_controller.add_instrument(new_instrument("lead"))
        project_controller.set_instrument_envelope(instrument.id, FeatureKey.VOLUME, Envelope(items=(15, 12)))
        editor.edit_instrument(instrument.id)
        return ReconstructionInstrumentsLogic(editor, scheduling=scheduling)

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
        instrument_logic.on_reconstruction_instrument_updated = lambda *args: regenerated.append(args)

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
