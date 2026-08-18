from typing import List, Tuple

import pytest

from sampletones_core.configs.display import (
    DISPLAY_HASH_LENGTH,
    DISPLAY_SEPARATOR,
    disambiguated_display_name,
    format_frequencies,
    format_generators,
    format_nes_frequency,
    format_sample_rate,
    format_transformation,
    format_transformation_gamma,
    short_hash,
    unique_display_names,
)
from sampletones_core.constants.enums import GeneratorName, SpectrumMethod


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


class TestFormatTransformationGamma:
    def test_marks_the_gamma(self) -> None:
        assert format_transformation_gamma(0) == "γ0"


class TestFormatGenerators:
    def test_reads_the_generators_in_the_order_they_are_given(self) -> None:
        assert (
            format_generators(
                [
                    GeneratorName.PULSE1,
                    GeneratorName.TRIANGLE,
                    GeneratorName.NOISE,
                ],
            )
            == "Pulse 1, Triangle, Noise"
        )

    def test_a_lone_generator_reads_as_its_own_name(self) -> None:
        assert format_generators([GeneratorName.PULSE2]) == "Pulse 2"

    def test_no_generator_reads_as_nothing(self) -> None:
        assert format_generators([]) == ""


class TestFormatFrequencies:
    def test_reads_audio_rate_then_frame_rate(self) -> None:
        assert format_frequencies(44100, 30) == "44.1 kHz·30 Hz"


class TestFormatTransformation:
    def test_reads_method_then_gamma(self) -> None:
        assert format_transformation(SpectrumMethod.FFT, 2) == "FFT·γ2"


class TestShortHash:
    def test_truncates_to_display_length(self) -> None:
        full = "6edf7c948606917a78b45d153c7ca7e0"
        assert short_hash(full) == full[:DISPLAY_HASH_LENGTH]
        assert len(short_hash(full)) == DISPLAY_HASH_LENGTH


class TestUniqueDisplayNames:
    @pytest.mark.parametrize(
        "entries, expected",
        [
            ([], []),
            ([("PTN", "aaaa1111")], ["PTN"]),
            ([("PTN", "aaaa1111"), ("PN", "bbbb2222")], ["PTN", "PN"]),
            (
                [("PTN", "aaaa1111"), ("PTN", "bbbb2222")],
                [
                    disambiguated_display_name("PTN", "aaaa1111"),
                    disambiguated_display_name("PTN", "bbbb2222"),
                ],
            ),
            (
                [("PTN", "aaaa1111"), ("PN", "bbbb2222"), ("PTN", "cccc3333")],
                [
                    disambiguated_display_name("PTN", "aaaa1111"),
                    "PN",
                    disambiguated_display_name("PTN", "cccc3333"),
                ],
            ),
        ],
    )
    def test_marks_only_the_shared_names(
        self,
        entries: List[Tuple[str, str]],
        expected: List[str],
    ) -> None:
        assert unique_display_names(entries) == tuple(expected)

    def test_keeps_the_given_order(self) -> None:
        entries = [("second", "aaaa1111"), ("first", "bbbb2222"), ("second", "cccc3333")]
        names = unique_display_names(entries)
        assert [name.split(DISPLAY_SEPARATOR)[0] for name in names] == ["second", "first", "second"]

    def test_names_stay_distinct(self) -> None:
        entries = [("PTN", "aaaa1111"), ("PTN", "bbbb2222"), ("PTN", "cccc3333")]
        assert len(set(unique_display_names(entries))) == len(entries)
