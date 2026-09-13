import json
from pathlib import Path
from typing import List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.headless.conversion.request import ConversionRequest, classic_setup
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.files import empty_file

RECONSTRUCTION = "sampletones_core.headless.conversion.runners.reconstruct"
LOADER = "sampletones_core.headless.config.load_config"


class RecordedReconstruction:
    def __init__(self) -> None:
        self.requests: List[ConversionRequest] = []

    def __call__(self, request: ConversionRequest, config: Config) -> None:
        del config
        self.requests.append(request)


@pytest.fixture(name="reconstruction")
def reconstruction_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedReconstruction:
    recorded = RecordedReconstruction()
    monkeypatch.setattr(RECONSTRUCTION, recorded)
    monkeypatch.setattr(LOADER, lambda path: Config())
    return recorded


def _two_stems() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=0,
                settings=StemSettings(channels=[ChannelName.PULSE1, ChannelName.PULSE2], bends=[ChannelName.PULSE1]),
            ),
            StemEntry(
                id=1,
                settings=StemSettings(channels=[ChannelName.TRIANGLE], bends=[ChannelName.TRIANGLE]),
            ),
        ],
        hierarchy=StemsHierarchy(levels=[[0], [1]]),
    )


class TestConvert:
    def test_the_channels_named_become_one_stem(self, reconstruction: RecordedReconstruction, tmp_path: Path) -> None:
        source = empty_file(tmp_path, "song.wav")
        output = tmp_path / "song.stn"

        status = dispatch(COMMANDS, ["convert", str(source), "--channels", "pulse1,pulse2", "-o", str(output)])

        assert status == 0
        request = reconstruction.requests[0]
        assert request.sources == (source,)
        assert request.stems == classic_setup([ChannelName.PULSE1, ChannelName.PULSE2])
        assert request.output_path == output

    def test_without_channels_the_usual_three_are_used(
        self,
        reconstruction: RecordedReconstruction,
        tmp_path: Path,
    ) -> None:
        source = empty_file(tmp_path, "song.wav")

        assert dispatch(COMMANDS, ["convert", str(source)]) == 0
        assert reconstruction.requests[0].stems == classic_setup(DEFAULT_CHANNELS)
        assert reconstruction.requests[0].output_path is None

    def test_a_stems_file_pairs_its_entries_with_the_sources_in_order(
        self,
        reconstruction: RecordedReconstruction,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        bass = empty_file(tmp_path, "bass.wav")
        lead = empty_file(tmp_path, "lead.wav")
        stems = _two_stems()
        setup = tmp_path / "stems.json"
        setup.write_text(json.dumps(stems.model_dump(mode="json")), encoding="utf-8")

        assert dispatch(COMMANDS, ["convert", str(bass), str(lead), "--stems", str(setup)]) == 0
        assert reconstruction.requests[0].stems == stems
        printed = capsys.readouterr().out
        assert "bass.wav: stem 0 on pulse1, pulse2, bending pulse1" in printed
        assert "lead.wav: stem 1 on triangle, bending triangle" in printed

    def test_a_setup_pairing_wrong_is_refused(self, reconstruction: RecordedReconstruction, tmp_path: Path) -> None:
        source = empty_file(tmp_path, "song.wav")
        setup = tmp_path / "stems.json"
        setup.write_text(json.dumps(_two_stems().model_dump(mode="json")), encoding="utf-8")

        with pytest.raises(SystemExit, match="1 sources for 2 stems"):
            dispatch(COMMANDS, ["convert", str(source), "--stems", str(setup)])

        assert reconstruction.requests == []

    def test_an_unknown_channel_is_refused(self, reconstruction: RecordedReconstruction, tmp_path: Path) -> None:
        source = empty_file(tmp_path, "song.wav")

        with pytest.raises(SystemExit, match="Unknown channel 'pulse3'"):
            dispatch(COMMANDS, ["convert", str(source), "--channels", "pulse3"])

        assert reconstruction.requests == []

    def test_a_missing_source_is_refused_in_one_line(
        self, reconstruction: RecordedReconstruction, tmp_path: Path
    ) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["convert", str(tmp_path / "absent.wav")])

        assert str(leaving.value) == f"No file at {tmp_path / 'absent.wav'}."
        assert reconstruction.requests == []

    def test_a_project_is_refused_as_no_recording(self, reconstruction: RecordedReconstruction, tmp_path: Path) -> None:
        project = empty_file(tmp_path, "song.stp")

        with pytest.raises(SystemExit, match="is no recording") as leaving:
            dispatch(COMMANDS, ["convert", str(project)])

        assert len(str(leaving.value).splitlines()) == 1
        assert reconstruction.requests == []

    def test_a_missing_stems_file_is_refused(self, reconstruction: RecordedReconstruction, tmp_path: Path) -> None:
        source = empty_file(tmp_path, "song.wav")

        with pytest.raises(SystemExit, match="No stems file at"):
            dispatch(COMMANDS, ["convert", str(source), "--stems", str(tmp_path / "absent.json")])

        assert reconstruction.requests == []

    def test_channels_and_stems_exclude_each_other(self, tmp_path: Path) -> None:
        source = empty_file(tmp_path, "song.wav")

        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["convert", str(source), "--channels", "pulse1", "--stems", "stems.json"])

        assert leaving.value.code == 2
