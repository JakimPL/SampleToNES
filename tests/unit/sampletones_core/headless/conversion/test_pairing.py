from pathlib import Path

from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.headless.conversion.pairing import describe_stem, pairing_lines
from sampletones_core.headless.conversion.request import ConversionRequest, classic_setup
from tests.unit.sampletones_core.headless.conversion.stems import recording, two_stems


class TestDescribeStem:
    def test_a_stem_names_its_channels_and_its_bends(self) -> None:
        first, second = two_stems().entries

        assert describe_stem(first) == "stem 0 on pulse1, pulse2, bending pulse1"
        assert describe_stem(second) == "stem 1 on noise"


class TestPairingLines:
    def test_recordings_pair_with_the_entries_in_order(self, tmp_path: Path) -> None:
        bass = recording(tmp_path, "bass.wav")
        drums = recording(tmp_path, "drums.wav")

        request = ConversionRequest(sources=(bass, drums), stems=two_stems(), output_path=None)

        assert pairing_lines(request) == [
            "bass.wav: stem 0 on pulse1, pulse2, bending pulse1",
            "drums.wav: stem 1 on noise",
        ]

    def test_a_directory_names_the_one_stem_every_recording_plays_under(self, tmp_path: Path) -> None:
        request = ConversionRequest(sources=(tmp_path,), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)

        assert pairing_lines(request) == [
            f"{tmp_path.name}/: every recording under stem 0 on pulse1, triangle, noise, bending pulse1, triangle"
        ]
