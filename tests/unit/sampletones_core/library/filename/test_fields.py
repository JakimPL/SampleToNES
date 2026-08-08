from dataclasses import dataclass
from typing import Type, Union

import pytest

from sampletones_core.library.filename.fields import (
    FILENAME_SEPARATOR,
    InstructionsFilenameFields,
)
from sampletones_core.paths import EXT_FILE_LIBRARY
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error

VALID_HASH: str = "a" * 32


def _fields(
    *,
    sr: int = 44100,
    nf: int = 60,
    ws: int = 2048,
    tg: int = 0,
    sm: str = "fft",
    ch: str = VALID_HASH,
) -> InstructionsFilenameFields:
    return InstructionsFilenameFields(sr=sr, nf=nf, ws=ws, tg=tg, sm=sm, ch=ch)


def _stem(
    *,
    sr: int = 44100,
    nf: int = 60,
    ws: int = 2048,
    tg: int = 0,
    sm: str = "fft",
    ch: str = VALID_HASH,
) -> str:
    return f"sr_{sr}_nf_{nf}_ws_{ws}_tg_{tg}_sm_{sm}_ch_{ch}"


class TestStem(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        fields: InstructionsFilenameFields
        expected: str

    test_cases = (
        TestCase(
            label="standard_values",
            fields=_fields(),
            expected=_stem(),
        ),
        TestCase(
            label="different_sample_rate",
            fields=_fields(sr=48000),
            expected=_stem(sr=48000),
        ),
        TestCase(
            label="different_nes_frequency",
            fields=_fields(nf=50),
            expected=_stem(nf=50),
        ),
        TestCase(
            label="nonzero_gamma",
            fields=_fields(tg=100),
            expected=_stem(tg=100),
        ),
        TestCase(
            label="mixed_hash_chars",
            fields=_fields(ch="0123456789abcdef" * 2),
            expected=_stem(ch="0123456789abcdef" * 2),
        ),
        TestCase(
            label="cqt_method",
            fields=_fields(sm="cqt"),
            expected=_stem(sm="cqt"),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_stem(self, test_case: TestCase) -> None:
        assert test_case.fields.stem == test_case.expected


class TestFilename(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        fields: InstructionsFilenameFields
        expected: str

    test_cases = (
        TestCase(
            label="appends_extension",
            fields=_fields(),
            expected=_stem() + EXT_FILE_LIBRARY,
        ),
        TestCase(
            label="different_config",
            fields=_fields(sr=22050, nf=30),
            expected=_stem(sr=22050, nf=30) + EXT_FILE_LIBRARY,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_filename(self, test_case: TestCase) -> None:
        assert test_case.fields.filename == test_case.expected


class TestCreate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        pathlike: str
        expected: Union[InstructionsFilenameFields, Type[Exception]]
        match: str = ""

    test_cases = (
        TestCase(
            label="valid_stem",
            pathlike=_stem(),
            expected=_fields(),
        ),
        TestCase(
            label="valid_stem_nonzero_gamma",
            pathlike=_stem(tg=75),
            expected=_fields(tg=75),
        ),
        TestCase(
            label="valid_stem_cqt_method",
            pathlike=_stem(sm="cqt"),
            expected=_fields(sm="cqt"),
        ),
        TestCase(
            label="valid_full_filename_with_extension",
            pathlike=_stem() + EXT_FILE_LIBRARY,
            expected=_fields(),
        ),
        TestCase(
            label="too_few_parts",
            pathlike=f"sr_44100_nf_60",
            expected=ValueError,
        ),
        TestCase(
            label="too_many_parts",
            pathlike=_stem() + "_extra_field",
            expected=ValueError,
        ),
        TestCase(
            label="wrong_key_at_nf_position",
            pathlike=f"sr_44100_cr_60_ws_2048_tg_0_sm_fft_ch_{VALID_HASH}",
            expected=ValueError,
            match="expected key 'nf', got 'cr'",
        ),
        TestCase(
            label="wrong_key_at_tg_position",
            pathlike=f"sr_44100_nf_60_ws_2048_gamma_0_sm_fft_ch_{VALID_HASH}",
            expected=ValueError,
            match="expected key 'tg'",
        ),
        TestCase(
            label="invalid_sr_not_integer",
            pathlike=f"sr_notanint_nf_60_ws_2048_tg_0_sm_fft_ch_{VALID_HASH}",
            expected=ValueError,
        ),
        TestCase(
            label="hash_too_short",
            pathlike=f"sr_44100_nf_60_ws_2048_tg_0_sm_fft_ch_abc",
            expected=ValueError,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_create(self, test_case: TestCase) -> None:
        if not expect_error(
            InstructionsFilenameFields.create,
            test_case.expected,
            test_case.pathlike,
            match=test_case.match or None,
        ):
            result = InstructionsFilenameFields.create(test_case.pathlike)
            assert isinstance(test_case.expected, InstructionsFilenameFields)
            assert result.sr == test_case.expected.sr
            assert result.nf == test_case.expected.nf
            assert result.ws == test_case.expected.ws
            assert result.tg == test_case.expected.tg
            assert result.sm == test_case.expected.sm
            assert result.ch == test_case.expected.ch


class TestRoundTrip(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        fields: InstructionsFilenameFields
        expected: str

    test_cases = (
        TestCase(
            label="standard",
            fields=_fields(),
            expected=_stem(),
        ),
        TestCase(
            label="high_sample_rate",
            fields=_fields(sr=96000, nf=120, ws=8192, tg=50),
            expected=_stem(sr=96000, nf=120, ws=8192, tg=50),
        ),
        TestCase(
            label="cqt_method",
            fields=_fields(sm="cqt"),
            expected=_stem(sm="cqt"),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_round_trip(self, test_case: TestCase) -> None:
        recovered = InstructionsFilenameFields.create(test_case.fields.stem)
        assert recovered.stem == test_case.expected
