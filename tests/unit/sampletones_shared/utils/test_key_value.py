from typing import Final, Optional

import pytest
from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.utils.key_value import key_value_name, parse_key_value_name

NAME: Final[str] = "rate_44100_mode_fft_tag_abc"


class Named(BaseModel):
    model_config = ConfigDict(frozen=True)

    rate: int = Field(gt=0)
    mode: str = Field(pattern=r"^[a-z]+$")
    tag: str


class TestAModelReadsBackFromTheNameItWrites:
    def test_the_name_spells_the_fields_in_their_declared_order(self) -> None:
        assert key_value_name(Named(rate=44100, mode="fft", tag="abc")) == NAME

    def test_a_written_name_parses_into_the_model_it_was_written_from(self) -> None:
        model = Named(rate=8000, mode="cqt", tag="x")
        assert parse_key_value_name(key_value_name(model), Named) == model

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "rate_44100",
            "rate_44100_mode_fft_tag_abc_extra_1",
            "mode_fft_rate_44100_tag_abc",
            "rate_044100_mode_fft_tag_abc",
            "rate_+44100_mode_fft_tag_abc",
            "rate_0_mode_fft_tag_abc",
            "rate_44100_mode_FFT_tag_abc",
            "rate_44100_mode_fft_tag_a_b",
            "rate_44100_mode_fft_label_abc",
            "rate__mode_fft_tag_abc",
            "rate_44100_mode_fft_tag_abc_",
            "_rate_44100_mode_fft_tag_abc",
        ],
    )
    def test_a_name_other_than_the_one_written_names_nothing(self, name: str) -> None:
        parsed: Optional[Named] = parse_key_value_name(name, Named)
        assert parsed is None
