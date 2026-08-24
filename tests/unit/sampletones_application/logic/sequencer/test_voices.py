from pathlib import Path
from typing import Callable, Dict, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.voices import SequencerVoicesLogic
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters.naming import instrument_slice_name
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.footprint import (
    features_footprint,
    reconstruction_footprints,
)
from sampletones_core.formats.famitracker.instrument import write_fti
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.instruments import (
    STANDALONE_INSTRUMENT_INDEX,
)
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind
from sampletones_core.formats.famitracker.voice import InstrumentOmission
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import LoadInstrumentError
from tests.suite.sequencer import sample_reconstruction


def _logic() -> Tuple[ProjectController, SequencerVoicesLogic]:
    controller = ProjectController(ProjectManager())
    logic = SequencerVoicesLogic(
        controller,
        MagicMock(),
        MagicMock(),
        scheduling=MagicMock(),
    )
    return controller, logic


def _logic_with_mocks() -> Tuple[
    ProjectController,
    SequencerVoicesLogic,
    MagicMock,
    MagicMock,
]:
    controller = ProjectController(ProjectManager())
    session_manager = MagicMock()
    audio_device_manager = MagicMock()
    logic = SequencerVoicesLogic(
        controller,
        session_manager,
        audio_device_manager,
        scheduling=MagicMock(),
    )
    return controller, logic, session_manager, audio_device_manager


def _place_instrument(
    controller: ProjectController,
    channel: ChannelName,
    voice_id: str,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        0,
        command=NoteOn(voice_id=voice_id),
    )


class TestSampleName:
    def test_returns_the_voice_name(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.voice_name(sample.id) == "lead"


class TestWhichKindAVoiceIs:
    def test_a_recording_answers_as_a_sample(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        assert logic.voice_kind(sample.id) is VoiceKind.SAMPLE

    def test_a_written_voice_answers_as_an_instrument(self) -> None:
        controller, logic = _logic()
        instrument = controller.add_instrument(Instrument(name="pad"))

        assert logic.voice_kind(instrument.id) is VoiceKind.INSTRUMENT

    def test_a_voice_the_pool_does_not_hold_answers_with_nothing(self) -> None:
        _, logic = _logic()

        assert logic.voice_kind("a-voice-no-project-holds") is None


class TestIsSampleUsed:
    def test_false_for_unreferenced_sample(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        assert logic.is_voice_used(sample.id) is False

    def test_true_after_placing_in_a_pattern(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, ChannelName.PULSE1, sample.id)
        assert logic.is_voice_used(sample.id) is True


class TestRemoveSample:
    def test_removes_unused_sample_from_pool(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        logic.remove_voice(sample.id)

        assert controller.project.voice(sample.id) is None

    def test_removing_used_sample_clears_its_references(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        _place_instrument(controller, ChannelName.PULSE1, sample.id)

        logic.remove_voice(sample.id)

        assert controller.project.voice(sample.id) is None
        assert logic.is_voice_used(sample.id) is False


class TestMoveSample:
    def test_move_sample_reorders_pool(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        controller.add_sample(reconstruction_factory(), name="second")

        logic.move_voice(first.id, 1)

        assert [sample.name for sample in controller.project.voices] == [
            "second",
            "first",
        ]


class TestDuplicateSample:
    def test_duplicate_sample_appends_copy(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        source = controller.add_sample(reconstruction_factory(), name="lead")

        logic.duplicate_voice(source.id)

        assert [sample.name for sample in controller.project.voices] == [
            "lead",
            "lead",
        ]


class TestBuildSamples:
    def test_lists_added_samples_in_insertion_order(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        first = controller.add_sample(reconstruction_factory(), name="first")
        second = controller.add_sample(reconstruction_factory(), name="second")

        view_model = logic.build_voices()

        assert [entry.voice_id for entry in view_model.voices] == [
            first.id,
            second.id,
        ]
        assert [entry.name for entry in view_model.voices] == [
            "first",
            "second",
        ]


class TestBuildSampleFootprint:
    """The samples menu prints what a sample occupies, measured the way the sample is placed."""

    def test_it_names_each_playing_channel(self) -> None:
        controller, logic = _logic()
        channels = (ChannelName.PULSE1, ChannelName.TRIANGLE)
        sample = controller.add_sample(sample_reconstruction(channels), name="bell")

        footprint = logic.build_voice_footprint(sample.id)

        assert footprint is not None
        assert [instrument.channel for instrument in footprint.instruments] == list(channels)

    def test_it_measures_the_sample_under_its_own_loop_flag(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        controller.set_voice_loop_point(sample.id, WHOLE_LOOP_POINT)

        footprint = logic.build_voice_footprint(sample.id)

        assert footprint == SampleFootprintViewModel.from_footprints(reconstruction_footprints(sample.reconstruction))

    def test_a_looping_sample_costs_what_a_one_shot_costs(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        """Each dimension keeps the length it was written at, so circling costs a sample nothing."""
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        one_shot = logic.build_voice_footprint(sample.id)

        controller.set_voice_loop_point(sample.id, WHOLE_LOOP_POINT)
        looping = logic.build_voice_footprint(sample.id)

        assert one_shot is not None and looping is not None
        assert looping.total_bytes == one_shot.total_bytes

    def test_each_channel_is_measured_as_the_instrument_it_sounds(self) -> None:
        """A channel's figure is the cost of its own instrument, and the channels differ.

        The triangle states a pitch alone where the pulse states a level and a waveform too, so
        the same frame written on each costs the triangle the less.
        """
        controller, logic = _logic()
        channels = (ChannelName.PULSE1, ChannelName.TRIANGLE)
        sample = controller.add_sample(sample_reconstruction(channels), name="bell")

        footprint = logic.build_voice_footprint(sample.id)

        assert footprint is not None
        assert footprint.bytes_for(ChannelName.TRIANGLE) < footprint.bytes_for(ChannelName.PULSE1)

    def test_a_sample_the_pool_has_dropped_is_measured_nowhere(self) -> None:
        _, logic = _logic()

        assert logic.build_voice_footprint("missing") is None


class TestTakingAChannelAsAnInstrument:
    """A recording's channel is read back as envelopes, so what it played becomes a voice to edit."""

    def test_every_channel_that_plays_is_offered(self) -> None:
        controller, logic = _logic()
        channels = (ChannelName.PULSE1, ChannelName.TRIANGLE)
        sample = controller.add_sample(sample_reconstruction(channels), name="bell")

        assert logic.instrument_channels(sample.id) == channels

    def test_a_voice_already_written_as_envelopes_offers_none(self) -> None:
        """It is what this would make of it, so there is nothing to take out of it."""
        controller, logic = _logic()
        instrument = logic.add_new_instrument("lead")

        assert logic.instrument_channels(instrument.id) == ()

    def test_a_voice_the_pool_has_dropped_offers_none(self) -> None:
        _, logic = _logic()

        assert logic.instrument_channels("missing") == ()

    def test_the_envelopes_come_across_as_the_channel_played_them(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction({ChannelName.TRIANGLE}), name="bell")
        played = sample.reconstruction.export()[ChannelName.TRIANGLE]

        instrument = logic.instrument_from_channel(sample.id, ChannelName.TRIANGLE)

        assert instrument is not None
        assert instrument.envelopes.volume == played.volume
        assert instrument.envelopes.arpeggio == played.arpeggio

    def test_the_instrument_is_measured_against_the_reference_that_channel_read(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction({ChannelName.NOISE}), name="bell")
        played = sample.reconstruction.export()[ChannelName.NOISE]

        instrument = logic.instrument_from_channel(sample.id, ChannelName.NOISE)

        assert instrument is not None
        assert instrument.reference(ChannelName.NOISE) == played.initial_pitch

    def test_the_instrument_is_named_after_the_channel_it_came_from(self) -> None:
        """A slice carries the name an export gives it, so the list says where the voice came from."""
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction({ChannelName.NOISE}), name="bell")

        instrument = logic.instrument_from_channel(sample.id, ChannelName.NOISE)

        assert instrument is not None
        assert instrument.name == instrument_slice_name("bell", ChannelName.NOISE)

    def test_the_instrument_holds_each_dimension_out_past_its_items(self) -> None:
        """A recorded channel rests on the value it last played, which is what a halt states."""
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction({ChannelName.PULSE1}), name="bell")

        instrument = logic.instrument_from_channel(sample.id, ChannelName.PULSE1)

        assert instrument is not None
        assert all(envelope.loop_point is None for envelope in instrument.envelopes.envelope_map.values())

    def test_taking_a_channel_leaves_the_pool_as_it_stands(self) -> None:
        """The instrument is written here and added by whoever asked, inside a history entry."""
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction({ChannelName.PULSE1}), name="bell")

        logic.instrument_from_channel(sample.id, ChannelName.PULSE1)

        assert controller.voice_count == 1

    def test_a_channel_standing_by_makes_nothing(self) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(sample_reconstruction({ChannelName.PULSE1}), name="bell")

        assert logic.instrument_from_channel(sample.id, ChannelName.NOISE) is None

    def test_a_voice_the_pool_has_dropped_makes_nothing(self) -> None:
        _, logic = _logic()

        assert logic.instrument_from_channel("missing", ChannelName.PULSE1) is None


class TestPlaySample:
    def test_plays_reconstruction_regardless_of_autoplay(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = False
        sample = controller.add_sample(reconstruction_factory(), name="lead")

        logic.play_voice(sample.id)

        audio_device_manager.play.assert_called_once()
        call = audio_device_manager.play.call_args
        assert np.array_equal(call.args[0], sample.reconstruction.approximation)
        assert call.kwargs["priority"] == PlaybackPriority.NORMAL
        assert call.kwargs["update"] is False

    def test_unknown_sample_is_ignored(self) -> None:
        _, logic, _, audio_device_manager = _logic_with_mocks()

        logic.play_voice("missing")

        audio_device_manager.play.assert_not_called()


class TestAutoplay:
    def test_executes_pending_preview_when_autoplay_enabled(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = True
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic._execute_autoplay()

        audio_device_manager.play.assert_called_once()
        assert audio_device_manager.play.call_args.kwargs["priority"] == PlaybackPriority.PREVIEW

    def test_skips_pending_preview_when_autoplay_disabled(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = False
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic._execute_autoplay()

        audio_device_manager.play.assert_not_called()

    def test_cancel_autoplay_drops_pending_preview(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = True
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic.cancel_autoplay()
        logic._execute_autoplay()

        audio_device_manager.play.assert_not_called()

    def test_request_edit_cancels_pending_preview(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        session_manager.autoplay = True
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        logic._pending_autoplay_sample = sample.id

        logic.request_edit(sample.id)
        logic._execute_autoplay()

        audio_device_manager.play.assert_not_called()


class TestInstrumentsInTheVoiceList:
    """A hand-written voice sits in the same list as a converted one, marked by its kind."""

    def test_an_instrument_is_listed_beside_the_samples_that_were_added(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller, logic = _logic()
        sample = controller.add_sample(reconstruction_factory(), name="bass")
        instrument = logic.add_new_instrument("lead")

        entries = logic.build_voices().voices

        assert [(entry.voice_id, entry.kind) for entry in entries] == [
            (sample.id, VoiceKind.SAMPLE),
            (instrument.id, VoiceKind.INSTRUMENT),
        ]

    def test_an_instrument_is_measured_as_the_one_export_it_writes(self) -> None:
        controller, logic = _logic()
        instrument = logic.add_new_instrument("lead")
        controller.set_instrument_envelope(instrument.id, FeatureKey.VOLUME, Envelope(items=(15, 12, 9)))

        footprint = logic.build_voice_footprint(instrument.id)

        assert footprint is not None
        assert footprint.total_bytes == features_footprint(instrument.instrument_features()).total_bytes
        assert [instrument.channel for instrument in footprint.instruments] == [None]

    def test_an_instrument_previews_through_the_pulse_channel(self) -> None:
        controller, logic, session_manager, audio_device_manager = _logic_with_mocks()
        instrument = logic.add_new_instrument("lead")
        controller.set_instrument_envelope(instrument.id, FeatureKey.VOLUME, Envelope(items=(15, 12)))

        logic.play_voice(instrument.id)

        played = audio_device_manager.play.call_args.args[0]
        assert played.size > 0

    def test_an_instrument_writing_nothing_sounds_no_preview(self) -> None:
        controller, logic, _, audio_device_manager = _logic_with_mocks()
        instrument = controller.add_instrument(Instrument(name="lead"))

        logic.play_voice(instrument.id)

        audio_device_manager.play.assert_not_called()


def _tracker_instrument(
    name: str,
    *sequences: InstrumentSequence,
) -> Instrument2A03:
    """A 2A03 instrument as a ``.fti`` holds one: every sequence stated, most of them empty."""
    written: Dict[SequenceKind, InstrumentSequence] = {kind: InstrumentSequence(kind=kind) for kind in SequenceKind}
    for sequence in sequences:
        written[sequence.kind] = sequence

    return Instrument2A03(
        index=STANDALONE_INSTRUMENT_INDEX,
        name=name,
        sequences=written,
    )


def _instrument_file(
    directory: Path,
    filename: str,
    name: str,
    *sequences: InstrumentSequence,
) -> Path:
    filepath = directory / filename
    write_fti(filepath, _tracker_instrument(name, *sequences))
    return filepath


class TestReadingAnInstrumentFile:
    """A ``.fti`` FamiTracker wrote arrives as a voice the pool holds like any other."""

    def test_the_envelopes_the_file_states_reach_the_voice(self, tmp_path: Path) -> None:
        filepath = _instrument_file(
            tmp_path,
            "Lead.fti",
            "Lead",
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15, 8, 0)),
            InstrumentSequence(kind=SequenceKind.ARPEGGIO, items=(0, 3, 7)),
        )
        _, logic = _logic()

        voice = logic.read_instrument(filepath).voice

        assert voice.envelopes.volume.items == (15, 8, 0)
        assert voice.envelopes.arpeggio.items == (0, 3, 7)

    def test_the_file_names_the_voice(self, tmp_path: Path) -> None:
        filepath = _instrument_file(
            tmp_path,
            "whatever.fti",
            "Lead",
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15,)),
        )
        _, logic = _logic()

        assert logic.read_instrument(filepath).voice.name == "Lead"

    def test_a_file_naming_nothing_leaves_the_voice_named_after_it(self, tmp_path: Path) -> None:
        """A nameless entry reads as nothing in the list, so the file it came from names it."""
        filepath = _instrument_file(
            tmp_path,
            "Bass Line.fti",
            "",
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15,)),
        )
        _, logic = _logic()

        assert logic.read_instrument(filepath).voice.name == "Bass Line"

    def test_what_the_file_states_past_the_voice_comes_back_with_it(self, tmp_path: Path) -> None:
        filepath = _instrument_file(
            tmp_path,
            "Lead.fti",
            "Lead",
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15, 8)),
            InstrumentSequence(kind=SequenceKind.PITCH, items=(1, -1)),
        )
        _, logic = _logic()

        assert InstrumentOmission.PITCH in logic.read_instrument(filepath).omissions

    def test_reading_leaves_the_pool_as_it_stands(self, tmp_path: Path) -> None:
        """The pool is edited by the gesture that adds, so a read alone records no history entry."""
        filepath = _instrument_file(
            tmp_path,
            "Lead.fti",
            "Lead",
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15,)),
        )
        controller, logic = _logic()

        logic.read_instrument(filepath)

        assert list(controller.project.voices) == []

    def test_the_voice_the_file_made_joins_the_pool(self, tmp_path: Path) -> None:
        filepath = _instrument_file(
            tmp_path,
            "Lead.fti",
            "Lead",
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15,)),
        )
        controller, logic = _logic()

        voice = logic.add_instrument(logic.read_instrument(filepath).voice)

        assert [entry.voice_id for entry in logic.build_voices().voices] == [voice.id]
        assert controller.project.voices.get(voice.id) is voice

    def test_a_file_of_another_kind_is_refused(self, tmp_path: Path) -> None:
        filepath = tmp_path / "notes.fti"
        filepath.write_bytes(b"not an instrument file at all")
        _, logic = _logic()

        with pytest.raises(LoadInstrumentError):
            logic.read_instrument(filepath)

    def test_a_file_that_ends_inside_its_own_layout_is_refused(self, tmp_path: Path) -> None:
        whole = _instrument_file(
            tmp_path,
            "Lead.fti",
            "Lead",
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15, 8, 0)),
        )
        truncated = tmp_path / "Short.fti"
        truncated.write_bytes(whole.read_bytes()[:12])
        _, logic = _logic()

        with pytest.raises(LoadInstrumentError):
            logic.read_instrument(truncated)

    def test_a_file_that_is_not_there_is_reported_as_missing(self, tmp_path: Path) -> None:
        _, logic = _logic()

        with pytest.raises(FileNotFoundError):
            logic.read_instrument(tmp_path / "nowhere.fti")
