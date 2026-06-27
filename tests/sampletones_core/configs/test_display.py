import pytest

from sampletones_core.configs.display import (
    DISPLAY_HASH_LENGTH,
    format_nes_frequency,
    format_sample_rate,
    short_hash,
)


class TestFormatSampleRate:
    @pytest.mark.parametrize(
        "sample_rate, expected",
        [
            (44100, "44.1 kHz"),
            (48000, "48 kHz"),
            (8000, "8 kHz"),
            (16000, "16 kHz"),
            (22050, "22.05 kHz"),
        ],
    )
    def test_renders_kilohertz(self, sample_rate: int, expected: str) -> None:
        assert format_sample_rate(sample_rate) == expected


class TestFormatNesFrequency:
    def test_appends_hertz_unit(self) -> None:
        assert format_nes_frequency(30) == "30 Hz"


class TestShortHash:
    def test_truncates_to_display_length(self) -> None:
        full = "6edf7c948606917a78b45d153c7ca7e0"
        assert short_hash(full) == full[:DISPLAY_HASH_LENGTH]
        assert len(short_hash(full)) == DISPLAY_HASH_LENGTH
