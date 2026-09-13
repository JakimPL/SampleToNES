import json
from pathlib import Path
from typing import List, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.headless import conversion
from sampletones_core.headless.conversion import (
    ConversionRequest,
    channels_named,
    classic_setup,
    describe_stem,
    load_stems,
    reconstruct,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


def _recording(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(b"")
    return path


def _two_stems() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=0,
                settings=StemSettings(channels=[ChannelName.PULSE1, ChannelName.PULSE2], bends=[ChannelName.PULSE1]),
            ),
            StemEntry(
                id=1,
                settings=StemSettings(channels=[ChannelName.NOISE], bends=[]),
            ),
        ],
        hierarchy=StemsHierarchy(levels=[[0, 1]]),
    )


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
        stems = _two_stems()
        path = tmp_path / "stems.json"
        path.write_text(json.dumps(stems.model_dump(mode="json")), encoding="utf-8")

        assert load_stems(path) == stems

    def test_a_file_holding_no_mapping_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "stems.json"
        path.write_text("[]", encoding="utf-8")

        with pytest.raises(TypeError, match="must hold a mapping"):
            load_stems(path)

    def test_a_mapping_that_is_no_setup_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "stems.json"
        path.write_text(json.dumps({"entries": [{"id": 0, "settings": {"channels": ["pulse9"], "bends": []}}]}))

        with pytest.raises(ValueError):
            load_stems(path)


class TestDescribeStem:
    def test_a_stem_names_its_channels_and_its_bends(self) -> None:
        first, second = _two_stems().entries

        assert describe_stem(first) == "stem 0 on pulse1, pulse2, bending pulse1"
        assert describe_stem(second) == "stem 1 on noise"


class TestConversionRequest:
    def test_recordings_pair_with_the_entries_in_order(self, tmp_path: Path) -> None:
        bass = _recording(tmp_path, "bass.wav")
        drums = _recording(tmp_path, "drums.wav")

        request = ConversionRequest(sources=(bass, drums), stems=_two_stems(), output_path=None)

        assert request.directory is None
        assert request.pairing() == [
            "bass.wav: stem 0 on pulse1, pulse2, bending pulse1",
            "drums.wav: stem 1 on noise",
        ]

    def test_a_directory_is_converted_file_by_file_under_one_stem(self, tmp_path: Path) -> None:
        request = ConversionRequest(sources=(tmp_path,), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)

        assert request.directory == tmp_path
        assert request.pairing() == [
            f"{tmp_path.name}/: every recording under stem 0 on pulse1, triangle, noise, bending pulse1, triangle"
        ]

    def test_a_count_mismatch_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="1 sources for 2 stems"):
            ConversionRequest(sources=(_recording(tmp_path, "bass.wav"),), stems=_two_stems(), output_path=None)

    def test_a_directory_under_several_stems_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="under one stem; the setup holds 2"):
            ConversionRequest(sources=(tmp_path,), stems=_two_stems(), output_path=None)

    def test_a_directory_among_recordings_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="one directory alone"):
            ConversionRequest(
                sources=(_recording(tmp_path, "bass.wav"), tmp_path), stems=_two_stems(), output_path=None
            )

    def test_an_output_path_for_a_directory_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="an output path names the one file"):
            ConversionRequest(
                sources=(tmp_path,),
                stems=classic_setup(DEFAULT_CHANNELS),
                output_path=tmp_path / "out.stn",
            )

    def test_no_source_is_refused(self) -> None:
        with pytest.raises(ValueError):
            ConversionRequest(sources=(), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)


class TestReconstruct:
    def test_recordings_are_mixed_into_one_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        calls: List[Tuple[Tuple[Path, ...], Path]] = []

        def reconstruct_sources(
            sources: Tuple[Path, ...], config: Config, stems: StemsConfig, output_path: Path
        ) -> None:
            del config, stems
            calls.append((sources, output_path))

        monkeypatch.setattr(conversion, "reconstruct_sources", reconstruct_sources)
        source = _recording(tmp_path, "song.wav")
        request = ConversionRequest(
            sources=(source,), stems=classic_setup(DEFAULT_CHANNELS), output_path=tmp_path / "x.stn"
        )

        reconstruct(request, Config())

        assert calls == [((source,), tmp_path / "x.stn")]

    def test_a_directory_is_walked(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        walked: List[Path] = []

        def reconstruct_directory(directory: Path, config: Config, stems: StemsConfig) -> None:
            del config, stems
            walked.append(directory)

        monkeypatch.setattr(conversion, "reconstruct_directory", reconstruct_directory)
        request = ConversionRequest(sources=(tmp_path,), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)

        reconstruct(request, Config())

        assert walked == [tmp_path]
