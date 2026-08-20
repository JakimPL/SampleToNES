from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, List
from unittest.mock import patch

import msgpack
import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, FeatureKey, HierarchyMode
from sampletones_core.data import Metadata
from sampletones_core.features import resting_reference
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.stems.data import (
    ChannelAssignment,
    StemsData,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_shared.application import (
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)
from sampletones_shared.constants.nes import DEFAULT_NES_FREQUENCY
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionValuesError,
    LoadReconstructionError,
    UnhandledReconstructionError,
)
from tests.conftest import ReconstructionFactory
from tests.suite.arrays import assert_array_equal
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import DIRECTORY_READ_ERRORS

_RETUNED_FREQUENCY: Final[int] = DEFAULT_NES_FREQUENCY // 2
_FASTER_FREQUENCY: Final[int] = DEFAULT_NES_FREQUENCY * 2

_AUDIO_LENGTH: Final[int] = 64
_BASE_PITCH: Final[int] = 60
_OCTAVE: Final[int] = 12
_CONTOUR_MIDPOINT: Final[int] = 66
_RESET_PITCH: Final[int] = 48


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _reconstruction(instructions: List[PulseInstruction]) -> Reconstruction:
    return Reconstruction.create(
        approximation=np.zeros(_AUDIO_LENGTH, dtype=np.float32),
        approximations={ChannelName.PULSE1: np.zeros(_AUDIO_LENGTH, dtype=np.float32)},
        instructions={ChannelName.PULSE1: instructions},
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def _saved_playing_channels_only(path: Path) -> Path:
    """Writes a reconstruction the way a file saved before the channel set holds one.

    Such a file names a stream for the channels it plays, leaving the rest to be filled in
    on the way back.
    """
    reconstruction = _reconstruction([_pulse(_BASE_PITCH)])
    reconstruction.instructions_data = [
        item for item in reconstruction.instructions_data if item.channel_name == ChannelName.PULSE1
    ]
    reconstruction.save(path)
    return path


class TestStemsDataRoundTrip:
    def test_stems_data_survives_save_and_load(self, tmp_path: Path) -> None:
        stems_config = StemsConfig(
            entries=[StemEntry(id=0, channels=[ChannelName.PULSE1])],
            hierarchy=StemsHierarchy(levels=[[0]], mode=HierarchyMode.STRICT),
            channel_cap=1,
        )
        stems_data = StemsData(
            config=stems_config,
            assignments=[
                ChannelAssignment(
                    channel_name=ChannelName.PULSE1,
                    stem_ids=[0, 0],
                )
            ],
        )
        reconstruction = Reconstruction.create(
            approximation=np.zeros(_AUDIO_LENGTH, dtype=np.float32),
            approximations={ChannelName.PULSE1: np.zeros(_AUDIO_LENGTH, dtype=np.float32)},
            instructions={ChannelName.PULSE1: [_pulse(_BASE_PITCH), _pulse(_BASE_PITCH)]},
            config=Config(),
            coefficient=1.0,
            audio_filepath=Path("/dev/null"),
            stems_data=stems_data,
        )
        path = tmp_path / "stems.stn"
        reconstruction.save(path)

        loaded = Reconstruction.load(path)

        assert loaded.stems_data == stems_data

    def test_load_without_stems_data_keeps_none(self, tmp_path: Path) -> None:
        path = tmp_path / "plain.stn"
        _reconstruction([_pulse(_BASE_PITCH)]).save(path)

        loaded = Reconstruction.load(path)

        assert loaded.stems_data is None

    def test_audio_filepath_tuple_survives_save_and_load(self, tmp_path: Path) -> None:
        stem_paths = (
            Path("/dev/null/stem_a.wav"),
            Path("/dev/null/stem_b.wav"),
        )
        reconstruction = Reconstruction.create(
            approximation=np.zeros(_AUDIO_LENGTH, dtype=np.float32),
            approximations={ChannelName.PULSE1: np.zeros(_AUDIO_LENGTH, dtype=np.float32)},
            instructions={ChannelName.PULSE1: [_pulse(_BASE_PITCH)]},
            config=Config(),
            coefficient=1.0,
            audio_filepath=stem_paths,
        )
        path = tmp_path / "stems_paths.stn"
        reconstruction.save(path)

        loaded = Reconstruction.load(path)

        assert loaded.audio_filepath == stem_paths


class TestRoundTrip:
    def test_save_load_round_trip(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()
        path = tmp_path / "demo.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert loaded.id == reconstruction.id
        assert loaded.coefficient == reconstruction.coefficient
        assert loaded.audio_filepath == reconstruction.audio_filepath
        assert_array_equal(loaded.approximation, reconstruction.approximation)

    def test_detached_source_round_trips_as_none(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction.detach_source()
        path = tmp_path / "detached.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert loaded.audio_filepath is None


class TestDetachSource:
    def test_detach_clears_the_source_location(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()
        assert reconstruction.audio_filepath is not None

        reconstruction.detach_source()

        assert reconstruction.audio_filepath is None


class TestLoadRejectsForeignFiles:
    def test_non_reconstruction_file_raises_load_error(self, tmp_path: Path) -> None:
        foreign = tmp_path / "kick.wav"
        foreign.write_bytes(b"RIFF\x58\xb9\x00\x00WAVEfmt " + b"\x00" * 256)

        with pytest.raises(LoadReconstructionError):
            Reconstruction.load(foreign)

    def test_corrupt_binary_raises_invalid_values(self) -> None:
        with pytest.raises(InvalidReconstructionValuesError):
            Reconstruction.deserialize_data(
                b"garbage-not-a-flatbuffer",
                source="corrupt.stn",
            )


class TestLoadFileAccess(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        make_path: Callable[[Path], Path]

    test_cases = (
        TestCase(
            label="missing_file",
            make_path=lambda root: root / "nope.stn",
            expected=FileNotFoundError,
        ),
        TestCase(
            label="directory",
            make_path=lambda root: root,
            expected=DIRECTORY_READ_ERRORS,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_inaccessible_path_raises(
        self,
        test_case: TestCase,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(test_case.expected):
            Reconstruction.load(test_case.make_path(tmp_path))


class TestMetadataValidation:
    def test_incompatible_version_propagates(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory().model_copy(
            update={
                "metadata": Metadata(reconstruction_data_version="0.0"),
            }
        )
        path = tmp_path / "old.stn"
        reconstruction.save(path)

        with pytest.raises(IncompatibleReconstructionVersionError) as exc_info:
            Reconstruction.load(path)

        assert exc_info.value.actual_version == "0.0"
        assert exc_info.value.expected_version == SAMPLETONES_RECONSTRUCTION_DATA_VERSION

    def test_foreign_application_name_propagates(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory().model_copy(
            update={
                "metadata": Metadata(application_name="Foreign"),
            }
        )
        path = tmp_path / "foreign.stn"
        reconstruction.save(path)

        with pytest.raises(InvalidMetadataError):
            Reconstruction.load(path)


class TestVersionUpgradeOnLoad:
    def test_a_2_1_file_loads_through_the_upgrade(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()
        path = tmp_path / "old.stn"
        reconstruction.save(path)

        binary = path.read_bytes()
        data = msgpack.unpackb(binary, raw=False)
        data["metadata"]["reconstruction_data_version"] = "2.1"
        for item in data["approximations_data"]:
            item["generator_name"] = item.pop("channel_name")

        for item in data["instructions_data"]:
            item["generator_name"] = item.pop("channel_name")

        generation = data["config"]["generation"]
        generation["generators"] = generation.pop("channels")
        config_metadata = data["config"].get("metadata")
        if isinstance(config_metadata, dict):
            config_metadata["reconstruction_data_version"] = "2.1"

        path.write_bytes(msgpack.packb(data, use_bin_type=True))

        loaded = Reconstruction.load(path)

        assert loaded.metadata.reconstruction_data_version == SAMPLETONES_RECONSTRUCTION_DATA_VERSION
        assert loaded.config.metadata.reconstruction_data_version == SAMPLETONES_RECONSTRUCTION_DATA_VERSION
        assert set(loaded.approximations) == set(reconstruction.approximations)


class TestDeserializeDataWrapping(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        side_effect: Exception

    test_cases = (
        TestCase(
            label="unexpected_wrapped_as_unhandled",
            side_effect=RuntimeError("runtime_error"),
            expected=UnhandledReconstructionError,
        ),
        TestCase(
            label="domain_error_propagates_unchanged",
            side_effect=DeserializationError("missing getter"),
            expected=DeserializationError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_deserialize_data_maps_error(self, test_case: TestCase) -> None:
        with patch.object(
            Reconstruction,
            "deserialize",
            side_effect=test_case.side_effect,
        ):
            with pytest.raises(test_case.expected):
                Reconstruction.deserialize_data(b"x", source="mem")


class TestInitialPitchReference:
    """The reference pitch each channel's arpeggio is measured against is stored, not re-derived.

    Storing it is what keeps an arpeggio edit from moving the base pitch: an edited contour
    carries absolute pitches, so deriving a reference from it again would follow the edit.
    """

    def test_create_anchors_each_generator_to_its_contour(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH), _pulse(_BASE_PITCH + _OCTAVE)])

        assert reconstruction.initial_pitches[ChannelName.PULSE1] == _CONTOUR_MIDPOINT

    def test_export_measures_the_arpeggio_against_the_stored_reference(self) -> None:
        """An arpeggiated channel exports offsets from the pitch it was anchored at.

        The channel is anchored flat at ``_BASE_PITCH`` and then given a contour an octave
        up on its first frame — the shape an ``12 0`` envelope produces. The export reports
        the stored reference and reads the octave straight back.
        """
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)
        arpeggiated = [
            _pulse(_BASE_PITCH + _OCTAVE),
            _pulse(_BASE_PITCH),
            _pulse(_BASE_PITCH),
        ]
        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            arpeggiated,
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
            (),
        )

        features = reconstruction.export()[ChannelName.PULSE1]

        assert features.initial_pitch == _BASE_PITCH
        assert features.arpeggio.tolist() == [_OCTAVE, 0]

    def test_update_generator_data_replaces_the_reference(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [_pulse(_RESET_PITCH)],
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _RESET_PITCH,
            (),
        )

        assert reconstruction.initial_pitches[ChannelName.PULSE1] == _RESET_PITCH

    def test_reference_survives_a_save_load_round_trip(self, tmp_path: Path) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH), _pulse(_BASE_PITCH + _OCTAVE)])
        path = tmp_path / "anchored.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert loaded.initial_pitches == reconstruction.initial_pitches


class TestHeldFeatures:
    """The dimensions each channel leaves to the channel travel with its instructions.

    A frame states every dimension, so an export reads which of them the instrument itself
    wrote from the reconstruction rather than from the frames.
    """

    def test_a_fresh_reconstruction_writes_every_dimension(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        assert reconstruction.held_features[ChannelName.PULSE1] == ()

    def test_a_held_dimension_exports_an_empty_envelope(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [_pulse(_BASE_PITCH)] * 3,
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
            (FeatureKey.ARPEGGIO,),
        )

        features = reconstruction.export()[ChannelName.PULSE1]
        assert features.arpeggio.size == 0
        assert features.volume.size > 0

    def test_the_written_dimensions_export_their_items(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [_pulse(_BASE_PITCH)] * 3,
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
            (FeatureKey.ARPEGGIO,),
        )

        features = reconstruction.export()[ChannelName.PULSE1]
        assert features.duty_cycle is not None
        assert features.duty_cycle.size > 0

    def test_the_record_reads_back_off_the_exported_envelopes(self) -> None:
        """What a reconstruction says it holds is what its export shows, on every channel.

        The record is the only place an empty envelope's meaning is kept, so a channel in play
        and one standing by both have to state the dimensions their export leaves empty.
        """
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [_pulse(_BASE_PITCH)] * 3,
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
            (FeatureKey.ARPEGGIO,),
        )

        exported = reconstruction.export()
        assert reconstruction.held_features == {
            channel_name: features.held_features for channel_name, features in exported.items()
        }

    def test_a_channel_standing_by_leaves_every_dimension_it_offers(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        assert reconstruction.held_features[ChannelName.TRIANGLE] == (
            FeatureKey.VOLUME,
            FeatureKey.ARPEGGIO,
        )
        assert reconstruction.held_features[ChannelName.NOISE] == (
            FeatureKey.VOLUME,
            FeatureKey.ARPEGGIO,
            FeatureKey.DUTY_CYCLE,
        )

    def test_clearing_the_last_frame_records_what_standing_by_records(self) -> None:
        """A channel edited out of play reads the same as one that never played."""
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [],
            np.zeros(0, dtype=np.float32),
            resting_reference(ChannelName.PULSE1),
            (FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE),
        )

        assert reconstruction.streams[ChannelName.PULSE1] == InstructionsItem.resting(ChannelName.PULSE1)

    def test_held_dimensions_survive_a_save_load_round_trip(self, tmp_path: Path) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)
        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [_pulse(_BASE_PITCH)] * 3,
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
            (FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE),
        )
        path = tmp_path / "held.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert loaded.held_features == reconstruction.held_features


class TestChannelSet:
    """A reconstruction holds every channel, so one that stands by stays editable.

    An instruction stream describing no frame is what a channel standing by looks like: it
    exports empty envelopes, costs nothing, and gaining a frame is what puts it in play.
    """

    def test_a_fresh_reconstruction_holds_every_channel(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        assert set(reconstruction.instructions) == set(ChannelName.items())
        assert reconstruction.playing_channels == (ChannelName.PULSE1,)

    def test_a_channel_standing_by_rests_at_the_shared_reference(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        assert reconstruction.initial_pitches[ChannelName.TRIANGLE] == resting_reference(ChannelName.TRIANGLE)
        assert reconstruction.initial_pitches[ChannelName.NOISE] == resting_reference(ChannelName.NOISE)

    def test_a_channel_standing_by_exports_empty_envelopes(self) -> None:
        features = _reconstruction([_pulse(_BASE_PITCH)]).export()[ChannelName.PULSE2]

        assert not features.has_frames
        assert features.volume.size == 0
        assert features.arpeggio.size == 0

    def test_a_channel_standing_by_renders_no_audio(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        assert ChannelName.PULSE2 not in reconstruction.approximations

    def test_clearing_every_frame_keeps_the_channel(self) -> None:
        """Taking a channel out of play leaves its stream in place, so the edit is reversible."""
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [],
            np.zeros(0, dtype=np.float32),
            _BASE_PITCH,
            (FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE),
        )

        assert reconstruction.playing_channels == ()
        assert ChannelName.PULSE1 in reconstruction.instructions
        assert reconstruction.initial_pitches[ChannelName.PULSE1] == _BASE_PITCH
        assert not reconstruction.export()[ChannelName.PULSE1].has_frames

    def test_a_frame_puts_a_channel_standing_by_into_play(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        reconstruction.update_channel_data(
            ChannelName.PULSE2,
            [_pulse(_BASE_PITCH)] * 2,
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
            (),
        )

        assert reconstruction.playing_channels == (ChannelName.PULSE1, ChannelName.PULSE2)
        assert reconstruction.export()[ChannelName.PULSE2].has_frames
        assert ChannelName.PULSE2 in reconstruction.approximations

    def test_a_reconstruction_of_channels_standing_by_stays_valid(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [],
            np.zeros(0, dtype=np.float32),
            _BASE_PITCH,
            (),
        )

        assert reconstruction.approximations == {}
        assert reconstruction.approximation.size == 0

    def test_the_channel_set_survives_a_save_load_round_trip(self, tmp_path: Path) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])
        path = tmp_path / "channels.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert set(loaded.instructions) == set(ChannelName.items())
        assert loaded.playing_channels == reconstruction.playing_channels
        assert loaded.initial_pitches == reconstruction.initial_pitches

    def test_a_file_storing_fewer_streams_reads_as_the_whole_channel_set(self, tmp_path: Path) -> None:
        loaded = Reconstruction.load(_saved_playing_channels_only(tmp_path / "one_channel.stn"))

        assert set(loaded.instructions) == set(ChannelName.items())
        assert loaded.playing_channels == (ChannelName.PULSE1,)
        assert loaded.initial_pitches[ChannelName.NOISE] == resting_reference(ChannelName.NOISE)
        assert not loaded.export()[ChannelName.TRIANGLE].has_frames

    def test_editing_such_a_file_writes_the_whole_channel_set(self, tmp_path: Path) -> None:
        loaded = Reconstruction.load(_saved_playing_channels_only(tmp_path / "one_channel.stn"))

        loaded.update_channel_data(
            ChannelName.PULSE2,
            [_pulse(_BASE_PITCH)],
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
            (),
        )

        assert [item.channel_name for item in loaded.instructions_data] == list(ChannelName.items())


class TestWithNesFrequency:
    def test_rebuilds_config(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert retuned.config.nes_frequency == _RETUNED_FREQUENCY
        assert retuned.config.frame_length == round(retuned.config.sample_rate / _RETUNED_FREQUENCY)

    def test_resynthesizes_approximation_length(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)
        faster = reconstruction.with_nes_frequency(_FASTER_FREQUENCY)

        generator_approximation = retuned.approximations[ChannelName.PULSE1]
        assert len(retuned.approximation) == len(generator_approximation)
        assert len(retuned.approximation) == retuned.config.frame_length
        assert len(faster.approximation) < len(retuned.approximation)

    def test_preserves_instructions(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert retuned.instructions == reconstruction.instructions
        assert retuned.coefficient == reconstruction.coefficient

    def test_leaves_original_untouched(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()
        original_frequency = reconstruction.config.nes_frequency
        original_length = len(reconstruction.approximation)

        reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert reconstruction.config.nes_frequency == original_frequency
        assert len(reconstruction.approximation) == original_length

    def test_a_channel_standing_by_stays_standing_by(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """A channel describing no frame renders nothing, so a retuned copy holds audio for the rest."""
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert set(retuned.approximations) == {ChannelName.PULSE1}
        assert set(retuned.instructions) == set(ChannelName.items())
        assert retuned.playing_channels == (ChannelName.PULSE1,)

    def test_a_reconstruction_of_channels_standing_by_retunes_to_silence(self) -> None:
        """Every channel standing by leaves nothing to render, and the retuned copy says so."""
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])
        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [],
            np.zeros(0, dtype=np.float32),
            _BASE_PITCH,
            (),
        )

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert retuned.config.nes_frequency == _RETUNED_FREQUENCY
        assert retuned.approximations == {}
        assert retuned.approximation.size == 0
        assert retuned.playing_channels == ()

    def test_matching_rate_returns_self(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(reconstruction.config.nes_frequency)

        assert retuned is reconstruction
