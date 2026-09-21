from pathlib import Path
from typing import Final, List, Sequence

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from sampletones_core.reconstructions.reconstruction.stems.source import StemSource
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

LEAD: Final[int] = 0
BASS: Final[int] = 1
RECORDINGS: Final[List[Path]] = [Path("/music/Lead Vocals.wav"), Path("/music/Bass.wav")]


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _stems_config() -> StemsConfig:
    channels = [ChannelName.PULSE1]
    return StemsConfig(
        entries=[
            StemEntry(id=stem_id, settings=StemSettings(channels=channels, bends=bending_channels(channels)))
            for stem_id in (LEAD, BASS)
        ],
        hierarchy=StemsHierarchy(levels=[[LEAD], [BASS]]),
    )


def _reconstruction(paths: Sequence[Path] = tuple(RECORDINGS)) -> Reconstruction:
    """Two recordings sharing the first pulse, one frame each, read from ``paths``."""
    return Reconstruction.create(
        instructions={ChannelName.PULSE1: [_pulse(60), _pulse(62)]},
        config=Config(),
        coefficient=1.0,
        audio_filepath=tuple(paths),
        stems_data=StemsData(
            config=_stems_config(),
            assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[LEAD, BASS])],
        ),
    )


class TestWhatTheRecordRemembersAboutARecording:
    def test_a_recording_is_named_after_the_file_it_was_read_from(self) -> None:
        reconstruction = _reconstruction()

        assert reconstruction.stems_data.named(LEAD) == "Lead Vocals"
        assert reconstruction.stems_data.named(BASS) == "Bass"

    def test_the_locations_read_back_in_entry_order(self) -> None:
        reconstruction = _reconstruction()

        assert reconstruction.audio_filepath == tuple(RECORDINGS)

    def test_the_sources_number_one_per_entry(self) -> None:
        with pytest.raises(ValueError, match="where the setup holds"):
            _reconstruction(paths=(RECORDINGS[0],))

    def test_a_record_naming_an_entry_the_setup_leaves_out_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="where the setup holds"):
            StemsData(
                config=_stems_config(),
                sources=[StemSource.of(LEAD, RECORDINGS[0]), StemSource.of(7, RECORDINGS[1])],
                assignments=[ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=[LEAD, BASS])],
            )


class TestADetachedDocument:
    def test_it_keeps_the_names_of_the_recordings_behind_it(self) -> None:
        reconstruction = _reconstruction()

        reconstruction.detach_source()

        assert reconstruction.stems_data.named(LEAD) == "Lead Vocals"
        assert reconstruction.stems_data.named(BASS) == "Bass"

    def test_it_states_no_location_at_all(self) -> None:
        reconstruction = _reconstruction()

        reconstruction.detach_source()

        assert reconstruction.audio_filepath == ()
        assert all(source.path is None for source in reconstruction.stems_data.sources)

    def test_it_keeps_the_setup_and_the_per_frame_record(self) -> None:
        reconstruction = _reconstruction()
        before = dict(reconstruction.stems_data.assignments_by_channel)

        reconstruction.detach_source()

        assert reconstruction.stems_data.config == _stems_config()
        assert reconstruction.stems_data.assignments_by_channel == before

    def test_it_carries_its_names_through_a_round_trip(self, tmp_path: Path) -> None:
        reconstruction = _reconstruction()
        reconstruction.detach_source()
        path = tmp_path / "detached.stn"

        reconstruction.save(path)
        restored = Reconstruction.load(path)

        assert restored.stems_data.named(LEAD) == "Lead Vocals"
        assert restored.audio_filepath == ()


class TestALocationOneRecordingHasLost:
    def test_the_whole_set_reads_as_unlocated(self) -> None:
        """One unreadable recording costs the whole original, so a partial set offers none."""
        reconstruction = _reconstruction()
        stems_data = reconstruction.stems_data
        partial = StemsData(
            config=stems_data.config,
            sources=[stems_data.sources_by_id[LEAD], stems_data.sources_by_id[BASS].detached()],
            assignments=stems_data.assignments,
        )

        assert partial.paths == ()
        assert partial.named(BASS) == "Bass"


class TestARecordingTakenOut:
    def test_its_source_leaves_the_record_with_it(self) -> None:
        reconstruction = _reconstruction()

        remaining = without_stem(reconstruction, LEAD)

        assert [source.stem_id for source in remaining.stems_data.sources] == [BASS]
        assert remaining.audio_filepath == (RECORDINGS[1],)

    def test_the_recordings_that_stay_keep_their_names(self) -> None:
        reconstruction = _reconstruction()

        remaining = without_stem(reconstruction, LEAD)

        assert remaining.stems_data.named(BASS) == "Bass"


class TestAnEditedDocument:
    def test_it_keeps_the_recordings_it_was_built_from(self) -> None:
        reconstruction = _reconstruction()

        reconstruction.update_channel_data(
            ChannelName.PULSE1,
            [_pulse(70), _pulse(72)],
            reconstruction.initial_pitches[ChannelName.PULSE1],
            reconstruction.held_features[ChannelName.PULSE1],
            heard=reconstruction.recorded_stem_ids,
        )

        assert reconstruction.audio_filepath == tuple(RECORDINGS)
        assert reconstruction.stems_data.named(LEAD) == "Lead Vocals"
