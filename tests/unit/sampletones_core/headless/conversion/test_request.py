import json
from pathlib import Path

import pytest

from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.headless.conversion.request import (
    ConversionRequest,
    channels_named,
    classic_setup,
    load_stems,
)
from tests.unit.sampletones_core.headless.conversion.stems import recording, two_stems


class TestChannelsNamed:
    def test_nothing_named_is_the_usual_three(self) -> None:
        assert channels_named(None) == list(DEFAULT_CHANNELS)

    def test_names_are_read_in_order_with_their_spaces_stripped(self) -> None:
        assert channels_named("noise, pulse1") == [ChannelName.NOISE, ChannelName.PULSE1]

    def test_an_unknown_name_is_refused_with_the_known_ones(self) -> None:
        with pytest.raises(ValueError, match="Unknown channel 'pulse3'; the channels are pulse1, pulse2"):
            channels_named("pulse1,pulse3")


class TestClassicSetup:
    def test_one_stem_holds_the_channels_in_order_and_bends_the_toned_ones(self) -> None:
        setup = classic_setup([ChannelName.NOISE, ChannelName.PULSE1])

        assert len(setup.entries) == 1
        assert setup.entries[0].settings.channels == [ChannelName.PULSE1, ChannelName.NOISE]
        assert setup.entries[0].settings.bends == [ChannelName.PULSE1]


class TestLoadStems:
    def test_a_setup_written_as_json_reads_back(self, tmp_path: Path) -> None:
        stems = two_stems()
        path = tmp_path / "stems.json"
        path.write_text(json.dumps(stems.model_dump(mode="json")), encoding="utf-8")

        assert load_stems(path) == stems

    def test_a_file_holding_no_mapping_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "stems.json"
        path.write_text("[]", encoding="utf-8")

        with pytest.raises(ValueError, match="must hold a mapping"):
            load_stems(path)

    def test_a_missing_file_is_refused_by_its_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No stems file at"):
            load_stems(tmp_path / "absent.json")

    def test_a_mapping_that_is_no_setup_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "stems.json"
        path.write_text(json.dumps({"entries": [{"id": 0, "settings": {"channels": ["pulse9"], "bends": []}}]}))

        with pytest.raises(ValueError):
            load_stems(path)


class TestConversionRequest:
    def test_recordings_pair_with_the_entries_in_order(self, tmp_path: Path) -> None:
        bass = recording(tmp_path, "bass.wav")
        drums = recording(tmp_path, "drums.wav")

        request = ConversionRequest(sources=(bass, drums), stems=two_stems(), output_path=None)

        assert request.directory is None
        assert request.sources == (bass, drums)

    def test_a_directory_is_converted_file_by_file_under_one_stem(self, tmp_path: Path) -> None:
        request = ConversionRequest(sources=(tmp_path,), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)

        assert request.directory == tmp_path

    def test_the_sources_are_classified_once_when_the_request_is_made(self, tmp_path: Path) -> None:
        directory = tmp_path / "recordings"
        directory.mkdir()
        request = ConversionRequest(sources=(directory,), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)

        directory.rmdir()

        assert request.directory == directory

    def test_a_count_mismatch_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="1 sources for 2 stems"):
            ConversionRequest(sources=(recording(tmp_path, "bass.wav"),), stems=two_stems(), output_path=None)

    def test_a_directory_under_several_stems_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="under one stem; the setup holds 2"):
            ConversionRequest(sources=(tmp_path,), stems=two_stems(), output_path=None)

    def test_a_directory_among_recordings_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="one directory alone"):
            ConversionRequest(sources=(recording(tmp_path, "bass.wav"), tmp_path), stems=two_stems(), output_path=None)

    def test_an_output_path_for_a_directory_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="an output path names the one file"):
            ConversionRequest(
                sources=(tmp_path,),
                stems=classic_setup(DEFAULT_CHANNELS),
                output_path=tmp_path / "out.stn",
            )

    def test_a_missing_source_is_refused_by_its_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No file at"):
            ConversionRequest(
                sources=(tmp_path / "absent.wav",),
                stems=classic_setup(DEFAULT_CHANNELS),
                output_path=None,
            )

    def test_a_file_other_than_a_recording_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="is no recording"):
            ConversionRequest(
                sources=(recording(tmp_path, "song.stp"),),
                stems=classic_setup(DEFAULT_CHANNELS),
                output_path=None,
            )

    def test_no_source_is_refused(self) -> None:
        with pytest.raises(ValueError):
            ConversionRequest(sources=(), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)
