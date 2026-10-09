from pathlib import Path
from typing import Final

from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.headless.conversion.pairing import describe_stem, pairing_lines
from sampletones_core.headless.conversion.request import ConversionRequest, classic_setup
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.files import empty_file
from tests.unit.sampletones_core.headless.conversion.stems import two_stems

LOUD_DRIVE: Final[float] = 2.0


class TestDescribeStem:
    def test_a_stem_names_its_channels_and_its_bends(self) -> None:
        first, second = two_stems().entries

        assert describe_stem(first) == "stem 0 on pulse1, pulse2, bending pulse1"
        assert describe_stem(second) == "stem 1 on noise"

    def test_a_stem_names_a_count_below_its_channels_and_a_drive_off_unit(self) -> None:
        entry = StemEntry(
            id=0,
            settings=StemSettings(
                channels=[ChannelName.PULSE1, ChannelName.PULSE2],
                bends=[],
                drives={ChannelName.PULSE1: LOUD_DRIVE},
                channel_cap=1,
            ),
        )

        assert describe_stem(entry) == "stem 0 on pulse1, pulse2, 1 at once, driving pulse1 at 2.00"


class TestPairingLines:
    def test_recordings_pair_with_the_entries_in_order(self, tmp_path: Path) -> None:
        bass = empty_file(tmp_path, "bass.wav")
        drums = empty_file(tmp_path, "drums.wav")

        request = ConversionRequest(sources=(bass, drums), stems=two_stems(), output_path=None)

        assert pairing_lines(request) == [
            "bass.wav: stem 0 on pulse1, pulse2, bending pulse1",
            "drums.wav: stem 1 on noise",
        ]

    def test_a_directory_names_the_one_stem_every_recording_plays_under(self, tmp_path: Path) -> None:
        setup = classic_setup(DEFAULT_CHANNELS)
        request = ConversionRequest(sources=(tmp_path,), stems=setup, output_path=None)

        assert pairing_lines(request) == [f"{tmp_path.name}/: every recording under {describe_stem(setup.entries[0])}"]
