from __future__ import annotations

from dataclasses import dataclass

import pytest

from sampletones.utils.system.locales import PREFERRED_ENCODING, to_utf8


class TestToUtf8:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        input_string: str
        encoding: str
        expected_result: str
        test_id: str

    @pytest.mark.parametrize(
        "test_case",
        [
            TestCase(
                input_string="Device Name",
                encoding="utf-8",
                expected_result="Device Name",
                test_id="ascii_utf8",
            ),
            TestCase(
                input_string="PÃ©riphÃ©rique Audio",
                encoding="latin-1",
                expected_result="Périphérique Audio",
                test_id="french_latin1",
            ),
            TestCase(
                input_string="PÃ©riphÃ©rique Audio",
                encoding="cp1252",
                expected_result="Périphérique Audio",
                test_id="french_cp1252",
            ),
            TestCase(
                input_string="UrzÄ…dzenie DĹşwiÄ™kowe",
                encoding="cp1250",
                expected_result="Urządzenie Dźwiękowe",
                test_id="polish_cp1250",
            ),
            TestCase(
                input_string="ZvukovĂ© zaĹ™Ă\xadzenĂ\xad",
                encoding="cp1250",
                expected_result="Zvukové zařízení",
                test_id="czech_cp1250",
            ),
            TestCase(
                input_string="РђСѓРґРёРѕСѓСЃС‚СЂРѕР№СЃС‚РІРѕ",
                encoding="cp1251",
                expected_result="Аудиоустройство",
                test_id="russian_cp1251",
            ),
            TestCase(
                input_string="п░я┐п╢п╦п╬я┐я│я┌я─п╬п╧я│я┌п╡п╬",
                encoding="koi8-r",
                expected_result="Аудиоустройство",
                test_id="russian_koi8r",
            ),
            TestCase(
                input_string="ط¬ظ‡ط§ط² طµظˆطھظٹ",
                encoding="cp1256",
                expected_result="جهاز صوتي",
                test_id="arabic_cp1256",
            ),
            TestCase(
                input_string="Ã\x84Ã¤nitelaite",
                encoding="latin-1",
                expected_result="Äänitelaite",
                test_id="finnish_latin1",
            ),
            TestCase(
                input_string="Dispositivo de Ã\x81udio",
                encoding="latin-1",
                expected_result="Dispositivo de Áudio",
                test_id="portuguese_latin1",
            ),
            TestCase(
                input_string="",
                encoding="utf-8",
                expected_result="",
                test_id="empty_string",
            ),
        ],
        ids=lambda tc: tc.test_id,
    )
    def test_to_utf8_with_various_encodings(self, test_case: TestToUtf8.TestCase) -> None:
        result = to_utf8(test_case.input_string, test_case.encoding)
        assert result == test_case.expected_result

    def test_to_utf8_with_default_encoding(self) -> None:
        result = to_utf8("Device Name")
        assert result == "Device Name"

    def test_to_utf8_already_utf8_string(self) -> None:
        utf8_string = "Ελληνικά Συσκευή"
        result = to_utf8(utf8_string, "utf-8")
        assert result == utf8_string

    def test_to_utf8_with_mixed_characters(self) -> None:
        mixed_string = "Device №123 • Status: ✓"
        result = to_utf8(mixed_string, "utf-8")
        assert result == mixed_string

    def test_to_utf8_ascii_only_works_with_any_encoding(self) -> None:
        ascii_string = "Simple ASCII Device"
        result_utf8 = to_utf8(ascii_string, "utf-8")
        result_latin1 = to_utf8(ascii_string, "latin-1")
        result_cp1252 = to_utf8(ascii_string, "cp1252")

        assert result_utf8 == ascii_string
        assert result_latin1 == ascii_string
        assert result_cp1252 == ascii_string

    def test_to_utf8_returns_original_on_unicode_decode_error(self) -> None:
        invalid_string = "Test\udcffString"
        result = to_utf8(invalid_string, "utf-8")
        assert result == invalid_string

    def test_to_utf8_returns_original_on_unicode_encode_error(self) -> None:
        unicode_string = "Emoji Device 🎵🔊"
        result = to_utf8(unicode_string, "ascii")
        assert result == unicode_string

    def test_to_utf8_handles_decode_error_with_invalid_bytes(self) -> None:
        string_with_surrogates = "\udcff\udcfe\udcfd"
        result = to_utf8(string_with_surrogates, "utf-8")
        assert result == string_with_surrogates

    def test_to_utf8_handles_encode_error_with_unsupported_chars(self) -> None:
        cyrillic_string = "Русский текст"
        result = to_utf8(cyrillic_string, "ascii")
        assert result == cyrillic_string

    def test_to_utf8_handles_encode_error_with_chinese_to_latin1(self) -> None:
        chinese_string = "中文设备"
        result = to_utf8(chinese_string, "latin-1")
        assert result == chinese_string

    def test_to_utf8_handles_encode_error_with_arabic_to_cp1252(self) -> None:
        arabic_string = "جهاز صوتي"
        result = to_utf8(arabic_string, "cp1252")
        assert result == arabic_string

    def test_to_utf8_handles_encode_error_with_emoji(self) -> None:
        emoji_string = "Device 😀🎵🔊💻"
        result = to_utf8(emoji_string, "cp1252")
        assert result == emoji_string

    def test_to_utf8_handles_mixed_invalid_characters(self) -> None:
        mixed_invalid = "Valid\udcffInvalid🎵Text"
        result = to_utf8(mixed_invalid, "ascii")
        assert result == mixed_invalid

    def test_to_utf8_with_special_characters(self) -> None:
        special_chars = "Device™ ©2024 – Audio®"
        result = to_utf8(special_chars, "cp1252")
        assert result == special_chars

    def test_to_utf8_with_preferred_encoding_constant(self) -> None:
        test_string = "Device Name"
        result = to_utf8(test_string, PREFERRED_ENCODING)
        assert result == test_string
        assert isinstance(result, str)

    def test_to_utf8_preserves_whitespace(self) -> None:
        string_with_whitespace = "  Device   Name  \t\n"
        result = to_utf8(string_with_whitespace, "utf-8")
        assert result == string_with_whitespace
