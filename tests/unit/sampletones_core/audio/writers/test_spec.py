from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_core.audio.writers import (
    AUDIO_DEPTHS,
    MP3_SAMPLE_RATES,
    AudioDepth,
    AudioFormat,
    Mp3OutputSpec,
    WaveOutputSpec,
    capability_of,
    default_mp3_bitrate,
    mp3_bitrates,
)
from sampletones_core.constants.audio import SAMPLE_RATES
from sampletones_core.paths import EXT_FILE_MP3, EXT_FILE_WAVE
from tests.suite.base import BaseTestSuite

MPEG_1_RATE: Final[int] = 44100
MPEG_2_RATE: Final[int] = 22050
MPEG_2_5_RATE: Final[int] = 8000


class TestWaveOutputSpec(BaseTestSuite):
    @pytest.mark.parametrize("sample_rate", SAMPLE_RATES)
    @pytest.mark.parametrize("depth", AUDIO_DEPTHS)
    def test_every_rate_and_depth_is_accepted(self, sample_rate: int, depth: AudioDepth) -> None:
        spec = WaveOutputSpec(sample_rate=sample_rate, depth=depth)

        assert spec.audio_format is AudioFormat.WAVE
        assert spec.sample_rate == sample_rate
        assert spec.depth is depth

    def test_the_extension_comes_from_the_capability(self) -> None:
        assert WaveOutputSpec(sample_rate=MPEG_1_RATE).extension == EXT_FILE_WAVE

    def test_a_rate_outside_the_offered_set_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="does not encode at 44101 Hz"):
            WaveOutputSpec(sample_rate=44101)

    def test_a_specification_is_frozen(self) -> None:
        spec = WaveOutputSpec(sample_rate=MPEG_1_RATE)

        with pytest.raises(ValidationError):
            spec.sample_rate = MPEG_2_RATE


class TestMp3OutputSpec(BaseTestSuite):
    @pytest.mark.parametrize("sample_rate", MP3_SAMPLE_RATES)
    def test_every_bitrate_on_the_ladder_is_accepted(self, sample_rate: int) -> None:
        for bitrate in mp3_bitrates(sample_rate):
            spec = Mp3OutputSpec(sample_rate=sample_rate, bitrate=bitrate)

            assert spec.audio_format is AudioFormat.MP3
            assert spec.bitrate == bitrate

    def test_the_extension_comes_from_the_capability(self) -> None:
        assert Mp3OutputSpec.at(MPEG_1_RATE).extension == EXT_FILE_MP3

    @pytest.mark.parametrize("sample_rate", (96000, 192000))
    def test_a_rate_the_encoder_rejects_is_rejected_here(self, sample_rate: int) -> None:
        """MPEG audio defines its sample rates, and 96 kHz is not among them."""
        with pytest.raises(ValidationError, match="does not encode at"):
            Mp3OutputSpec(sample_rate=sample_rate, bitrate=192)

    def test_a_bitrate_above_the_rate_s_ladder_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="does not encode at 320 kbps"):
            Mp3OutputSpec(sample_rate=MPEG_2_RATE, bitrate=320)

    def test_a_bitrate_off_the_ladder_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="does not encode at 200 kbps"):
            Mp3OutputSpec(sample_rate=MPEG_1_RATE, bitrate=200)

    @pytest.mark.parametrize(
        ("sample_rate", "expected"),
        (
            (MPEG_1_RATE, 192),
            (48000, 192),
            (MPEG_2_RATE, 160),
            (16000, 160),
            (MPEG_2_5_RATE, 64),
        ),
    )
    def test_the_default_bitrate_is_the_best_the_rate_reaches(self, sample_rate: int, expected: int) -> None:
        assert default_mp3_bitrate(sample_rate) == expected
        assert Mp3OutputSpec.at(sample_rate).bitrate == expected


class TestFormatCapabilities(BaseTestSuite):
    def test_wave_stores_samples_and_mp3_does_not(self) -> None:
        assert capability_of(AudioFormat.WAVE).stores_samples
        assert not capability_of(AudioFormat.MP3).stores_samples

    def test_the_mp3_rates_are_the_rates_a_ladder_is_declared_for(self) -> None:
        assert capability_of(AudioFormat.MP3).sample_rates == MP3_SAMPLE_RATES
        assert all(mp3_bitrates(sample_rate) for sample_rate in MP3_SAMPLE_RATES)

    def test_the_ladders_run_from_highest_to_lowest(self) -> None:
        for sample_rate in MP3_SAMPLE_RATES:
            bitrates = mp3_bitrates(sample_rate)

            assert list(bitrates) == sorted(bitrates, reverse=True)

    def test_the_wave_rates_are_the_rates_the_application_offers(self) -> None:
        assert capability_of(AudioFormat.WAVE).sample_rates == tuple(SAMPLE_RATES)
