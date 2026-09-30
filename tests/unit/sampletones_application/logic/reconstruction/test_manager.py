from pathlib import Path
from typing import Callable, Final, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, HierarchyMode, bending_channels
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.exceptions import LoadReconstructionError
from tests.suite.errors import DIRECTORY_READ_ERRORS
from tests.suite.stems import RECORDED_SCALE, single_entry_stems_data

SAMPLE_VOICE_ID: Final[str] = "lead-id"


def _two_entry_stems_data() -> StemsData:
    return StemsData(
        config=StemsConfig(
            entries=[
                StemEntry(
                    id=0,
                    settings=StemSettings(channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])),
                ),
                StemEntry(
                    id=1,
                    settings=StemSettings(channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])),
                ),
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1]], mode=HierarchyMode.STRICT),
        ),
        assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[0, 1])],
        scale=RECORDED_SCALE,
    )


def _two_frames() -> List[PulseInstruction]:
    """A frame for each of the two recordings, which every recording a document names holds."""
    return [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)] * 2


class TestLoadReconstructionPropagatesErrors:
    @staticmethod
    def _manager() -> ReconstructionManager:
        return ReconstructionManager(scheduling=MagicMock())

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            self._manager().load_reconstruction(tmp_path / "nope.stn")

    def test_directory_raises_directory_read_error(self, tmp_path: Path) -> None:
        with pytest.raises(DIRECTORY_READ_ERRORS):
            self._manager().load_reconstruction(tmp_path)

    def test_foreign_file_raises_load_reconstruction_error(self, tmp_path: Path) -> None:
        foreign = tmp_path / "kick.wav"
        foreign.write_bytes(b"RIFF\x58\xb9\x00\x00WAVEfmt " + b"\x00" * 256)

        with pytest.raises(LoadReconstructionError):
            self._manager().load_reconstruction(foreign)


class TestReconstructionManagerLoadReconstruction:
    def test_load_reconstruction_from_file_marks_session_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        save_path = tmp_path / "song.stn"
        reconstruction_factory().save(save_path)
        reconstruction_manager.load_reconstruction(save_path)
        assert reconstruction_manager.session.is_loaded

    def test_load_reconstruction_from_file_keeps_extension_in_session_name(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        save_path = tmp_path / "song.stn"
        reconstruction_factory().save(save_path)
        reconstruction_manager.load_reconstruction(save_path)
        assert reconstruction_manager.session.name == save_path.name

    def test_load_reconstruction_from_file_fires_callback(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        save_path = tmp_path / "song.stn"
        reconstruction_factory().save(save_path)
        callback = MagicMock()
        reconstruction_manager.on_reconstruction_loaded = callback
        reconstruction_manager.load_reconstruction(save_path)
        callback.assert_called_once()


class TestReconstructionManagerSaveReconstruction:
    def test_save_with_explicit_path_saves_file(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        save_path = tmp_path / "saved.stn"
        assert reconstruction_manager.save_reconstruction(save_path)
        assert save_path.exists()

    def test_save_with_no_path_and_no_filepath_is_no_op(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        assert not reconstruction_manager.save_reconstruction()

    def test_save_when_nothing_loaded_is_no_op(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        assert not reconstruction_manager.save_reconstruction(tmp_path / "out.stn")


class TestReconstructionManagerIsFileBacked:
    def test_false_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        assert not reconstruction_manager.is_file_backed

    def test_false_for_in_memory_object(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        assert not reconstruction_manager.is_file_backed

    def test_true_after_file_load(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        save_path = tmp_path / "song.stn"
        reconstruction_factory().save(save_path)
        reconstruction_manager.load_reconstruction(save_path)
        assert reconstruction_manager.is_file_backed


class TestTheFileADocumentIsBackedBy:
    """A conversion can write over the file the open document came from, so the manager tells its
    own file however the path to it is spelled."""

    @pytest.fixture(name="opened")
    def opened_fixture(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> Path:
        path = tmp_path / "song.stn"
        reconstruction_factory().save(path)
        reconstruction_manager.load_reconstruction(path)
        return path

    def test_the_file_it_was_loaded_from(
        self,
        reconstruction_manager: ReconstructionManager,
        opened: Path,
    ) -> None:
        assert reconstruction_manager.is_backed_by(opened)

    def test_the_same_file_spelled_another_way(
        self,
        reconstruction_manager: ReconstructionManager,
        opened: Path,
    ) -> None:
        (opened.parent / "folder").mkdir()

        assert reconstruction_manager.is_backed_by(opened.parent / "folder" / ".." / opened.name)

    def test_another_file(
        self,
        reconstruction_manager: ReconstructionManager,
        opened: Path,
    ) -> None:
        assert not reconstruction_manager.is_backed_by(opened.with_name("other.stn"))

    def test_nothing_open(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        assert not reconstruction_manager.is_backed_by(tmp_path / "song.stn")

    def test_a_document_held_in_memory(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )

        assert not reconstruction_manager.is_backed_by(tmp_path / "Sample.stn")


class TestReconstructionManagerSaveReconstructionAs:
    def test_writes_the_file(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        target = tmp_path / "detached.stn"
        reconstruction_manager.save_reconstruction_as(target)
        assert target.exists()

    def test_rebinds_to_a_file_backed_document(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        target = tmp_path / "detached.stn"
        reconstruction_manager.save_reconstruction_as(target)
        assert reconstruction_manager.is_file_backed
        assert reconstruction_manager.filepath == target

    def test_severs_reconstruction_identity_from_the_original(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        original = reconstruction_factory()
        reconstruction_manager.load_reconstruction_object(original, name="Sample", voice_id=SAMPLE_VOICE_ID)
        reconstruction_manager.save_reconstruction_as(tmp_path / "detached.stn")
        assert reconstruction_manager.reconstruction is not original

    def test_marks_session_saved(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        reconstruction_manager.mark_updated()
        reconstruction_manager.save_reconstruction_as(tmp_path / "detached.stn")
        assert not reconstruction_manager.session.unsaved_changes
        assert reconstruction_manager.session.is_loaded

    def test_no_op_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.save_reconstruction_as(tmp_path / "detached.stn")
        assert reconstruction_manager.current_reconstruction is None


class TestReconstructionManagerLoadObject:
    def test_load_object_marks_session_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        assert reconstruction_manager.session.is_loaded

    def test_load_object_sets_current_reconstruction(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        assert reconstruction_manager.current_reconstruction is not None

    def test_load_object_uses_supplied_name_for_session(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Kick drum",
            voice_id=SAMPLE_VOICE_ID,
        )
        assert reconstruction_manager.session.name == "Kick drum"

    def test_load_object_sets_reconstruction_by_identity(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction_manager.load_reconstruction_object(reconstruction, name="Sample", voice_id=SAMPLE_VOICE_ID)
        assert reconstruction_manager.reconstruction is reconstruction

    def test_load_object_fires_on_reconstruction_loaded_callback(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        callback = MagicMock()
        reconstruction_manager.on_reconstruction_loaded = callback
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        callback.assert_called_once()


class TestReconstructionManagerDetachCurrent:
    def test_detach_drops_filepath_and_keeps_object_identity(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        save_path = tmp_path / "kick.stn"
        reconstruction_factory().save(save_path)
        reconstruction_manager.load_reconstruction(save_path)
        loaded = reconstruction_manager.reconstruction

        reconstruction_manager.detach_current_reconstruction()

        assert reconstruction_manager.filepath is None
        assert reconstruction_manager.reconstruction is loaded

    def test_detach_without_loaded_reconstruction_is_no_op(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        reconstruction_manager.detach_current_reconstruction()
        assert reconstruction_manager.current_reconstruction is None


class TestReconstructionManagerClose:
    def test_close_resets_current_reconstruction_to_none(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        reconstruction_manager.close_reconstruction()
        assert reconstruction_manager.current_reconstruction is None

    def test_close_fires_on_reconstruction_closed_callback(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        callback = MagicMock()
        reconstruction_manager.on_reconstruction_closed = callback
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        reconstruction_manager.close_reconstruction()
        callback.assert_called_once()

    def test_close_marks_session_closed(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        reconstruction_manager.close_reconstruction()
        assert not reconstruction_manager.session.is_loaded

    def test_close_resets_source_paths_to_empty(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        reconstruction_manager.close_reconstruction()
        assert reconstruction_manager.source_paths == ()


class TestReconstructionManagerProperties:
    def test_reconstruction_property_returns_the_reconstruction_object(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction_manager.load_reconstruction_object(reconstruction, name="Sample", voice_id=SAMPLE_VOICE_ID)
        assert reconstruction_manager.reconstruction is reconstruction

    def test_filepath_property_is_none_for_in_memory_reconstruction(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        assert reconstruction_manager.filepath is None

    def test_source_paths_return_reconstruction_source_paths(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction_manager.load_reconstruction_object(reconstruction, name="Sample", voice_id=SAMPLE_VOICE_ID)
        assert reconstruction_manager.source_paths == reconstruction.audio_filepath

    def test_current_features_is_populated_after_load(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        assert reconstruction_manager.current_features is not None


class TestReconstructionManagerPropertiesWhenEmpty:
    def test_reconstruction_is_none_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        assert reconstruction_manager.reconstruction is None

    def test_filepath_is_none_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        assert reconstruction_manager.filepath is None

    def test_source_paths_are_empty_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        assert reconstruction_manager.source_paths == ()


class TestAnEditLettingARecordingGo:
    """The open document follows an edit that lets a recording go, and so does what is heard of it."""

    @staticmethod
    def _edited(reconstruction: Reconstruction) -> Reconstruction:
        """The document with the second recording's frame written silent, which it held alone."""
        edited = reconstruction.model_copy(deep=True)
        edited.update_channel_data(
            ChannelName.PULSE1,
            [_two_frames()[0], PulseInstruction.null_instruction()],
            edited.initial_pitches[ChannelName.PULSE1],
            edited.held_features[ChannelName.PULSE1],
            heard=edited.recorded_stem_ids,
        )
        return edited

    def test_the_recording_leaves_what_the_reader_hears(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        reconstruction = Reconstruction.create(
            instructions={ChannelName.PULSE1: _two_frames()},
            config=Config(),
            coefficient=1.0,
            audio_filepath=(tmp_path / "kick.wav", tmp_path / "snare.wav"),
            stems_data=_two_entry_stems_data(),
        )
        reconstruction_manager.load_reconstruction_object(reconstruction, name="Sample", voice_id=SAMPLE_VOICE_ID)

        reconstruction_manager.apply_edited(self._edited(reconstruction))

        assert reconstruction_manager.listening.offered == {0: frozenset({ChannelName.PULSE1})}
        assert reconstruction_manager.source_paths == (tmp_path / "kick.wav",)
        features = reconstruction_manager.current_features
        assert features is not None
        assert features[ChannelName.PULSE1].volume.items[-1] == 0


class TestTheVoiceTheDocumentIs:
    """The open document remembers the project voice it is, which is how the tab follows it."""

    def test_a_project_sample_names_its_voice(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )

        assert reconstruction_manager.voice_id == SAMPLE_VOICE_ID
        assert reconstruction_manager.is_project_sample

    def test_a_file_names_no_voice(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "song.stn"
        reconstruction_factory().save(path)
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )

        reconstruction_manager.load_reconstruction(path)

        assert reconstruction_manager.voice_id is None
        assert not reconstruction_manager.is_project_sample

    def test_an_edit_keeps_the_voice(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )

        reconstruction_manager.apply_edited(reconstruction_factory())

        assert reconstruction_manager.voice_id == SAMPLE_VOICE_ID

    def test_save_as_lets_the_voice_go(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        """The saved copy is a standalone document, so its edits reach only its file."""
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )

        reconstruction_manager.save_reconstruction_as(tmp_path / "detached.stn")

        assert reconstruction_manager.voice_id is None

    def test_a_failed_save_as_keeps_the_voice(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )

        with pytest.raises(OSError):
            reconstruction_manager.save_reconstruction_as(tmp_path / "missing" / "detached.stn")

        assert reconstruction_manager.voice_id == SAMPLE_VOICE_ID

    def test_closing_lets_the_voice_go(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )

        reconstruction_manager.close_reconstruction()

        assert reconstruction_manager.voice_id is None
        assert not reconstruction_manager.is_project_sample


class TestReconstructionManagerMarkUpdated:
    def test_mark_updated_sets_unsaved_changes(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(
            reconstruction_factory(),
            name="Sample",
            voice_id=SAMPLE_VOICE_ID,
        )
        reconstruction_manager.mark_updated()
        assert reconstruction_manager.session.unsaved_changes


class TestReconstructionManagerInternalGuards:
    def test_load_features_without_reconstruction_raises_runtime_error(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        with pytest.raises(RuntimeError):
            reconstruction_manager._load_reconstruction_features()


class TestReconstructionManagerLocateOriginalAudio:
    def test_locate_audio_raises_file_not_found_when_audio_missing(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        missing_path = tmp_path / "ghost.wav"
        reconstruction = Reconstruction.create(
            instructions={ChannelName.PULSE1: [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)]},
            config=Config(),
            coefficient=1.0,
            audio_filepath=(missing_path,),
            stems_data=single_entry_stems_data(
                [ChannelName.PULSE1],
                {ChannelName.PULSE1: [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)]},
            ),
        )
        reconstruction_manager.load_reconstruction_object(reconstruction, name="Sample", voice_id=SAMPLE_VOICE_ID)
        with pytest.raises(FileNotFoundError):
            reconstruction_manager.locate_original_audio()

    def test_locate_audio_returns_silently_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        reconstruction_manager.locate_original_audio()

    def test_locate_audio_opens_the_recorded_paths(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        first = tmp_path / "kick.wav"
        second = tmp_path / "snare.wav"
        write_wave(first, Config().library.sample_rate, np.ones(64, dtype=np.float32))
        write_wave(second, Config().library.sample_rate, np.ones(64, dtype=np.float32))
        reconstruction = Reconstruction.create(
            instructions={ChannelName.PULSE1: _two_frames()},
            config=Config(),
            coefficient=1.0,
            audio_filepath=(first, second),
            stems_data=_two_entry_stems_data(),
        )
        reconstruction_manager.load_reconstruction_object(reconstruction, name="Sample", voice_id=SAMPLE_VOICE_ID)

        with patch("sampletones_application.logic.reconstruction.manager.open_paths_in_explorer") as open_paths:
            reconstruction_manager.locate_original_audio()

        open_paths.assert_called_once_with((first, second))

    def test_locate_audio_reports_the_first_missing_path(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        present = tmp_path / "kick.wav"
        missing = tmp_path / "gone.wav"
        write_wave(present, Config().library.sample_rate, np.ones(64, dtype=np.float32))
        reconstruction = Reconstruction.create(
            instructions={ChannelName.PULSE1: _two_frames()},
            config=Config(),
            coefficient=1.0,
            audio_filepath=(present, missing),
            stems_data=_two_entry_stems_data(),
        )
        reconstruction_manager.load_reconstruction_object(reconstruction, name="Sample", voice_id=SAMPLE_VOICE_ID)

        with pytest.raises(FileNotFoundError) as raised:
            reconstruction_manager.locate_original_audio()

        assert raised.value.filename == str(missing)
