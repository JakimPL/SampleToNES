import re
from pathlib import Path
from typing import Final

import pytest

from sampletones_application.categories.elements.global_ import DialogElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key.text import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN
from sampletones_shared.exceptions import MalformedTextKeyError, MissingTextError
from sampletones_shared.utils.serialization import load_yaml

OK_STRING_KEY: Final[str] = "global.dialog.label.ok"
OK_TEXT_KEY: Final[TextKey] = TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.OK)


@pytest.fixture
def language_manager() -> LanguageManager:
    return LanguageManager(LANG_EN)


def write_language_file(path: Path, body: str) -> Path:
    language_path = path / "language.yaml"
    language_path.write_text(body, encoding="utf-8")
    return language_path


class TestLanguageManagerLookup:
    def test_string_key_resolves_the_text(self, language_manager: LanguageManager) -> None:
        assert language_manager[OK_STRING_KEY] == "OK"

    def test_string_key_and_tuple_agree(self, language_manager: LanguageManager) -> None:
        tuple_text = language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.OK]
        assert language_manager[OK_STRING_KEY] == tuple_text

    def test_string_key_and_text_key_agree(self, language_manager: LanguageManager) -> None:
        assert language_manager[OK_STRING_KEY] == language_manager[OK_TEXT_KEY]

    def test_every_key_of_the_language_file_resolves(self, language_manager: LanguageManager) -> None:
        keys = load_yaml(LANG_EN)
        assert isinstance(keys, dict)
        for key in keys:
            assert isinstance(language_manager[str(key)], str)

    def test_an_absent_key_is_named_in_the_report(self, language_manager: LanguageManager) -> None:
        with pytest.raises(MissingTextError, match=r"global\.dialog\.label\.absent_element"):
            _ = language_manager["global.dialog.label.absent_element"]

    def test_an_absent_key_reports_the_language_file(self, language_manager: LanguageManager) -> None:
        with pytest.raises(MissingTextError, match=re.escape(str(LANG_EN))):
            _ = language_manager["global.dialog.label.absent_element"]

    def test_a_malformed_key_reports_the_grammar(self, language_manager: LanguageManager) -> None:
        with pytest.raises(MalformedTextKeyError):
            _ = language_manager["global.dialog.ok"]

    def test_a_key_of_the_wrong_case_reports_the_grammar(self, language_manager: LanguageManager) -> None:
        with pytest.raises(MalformedTextKeyError):
            _ = language_manager["GLOBAL.DIALOG.LABEL.OK"]


class TestLanguageManagerLoad:
    def test_loading_replaces_the_held_text(self, tmp_path: Path) -> None:
        language_path = write_language_file(tmp_path, f"{OK_STRING_KEY}: Fine\n")
        language_manager = LanguageManager(language_path)
        assert language_manager[OK_STRING_KEY] == "Fine"

    def test_a_malformed_key_in_the_file_is_rejected(self, tmp_path: Path) -> None:
        language_path = write_language_file(tmp_path, "global.dialog.label: Fine\n")
        with pytest.raises(MalformedTextKeyError, match=r"global\.dialog\.label"):
            LanguageManager(language_path)

    def test_an_unknown_panel_in_the_file_is_rejected(self, tmp_path: Path) -> None:
        language_path = write_language_file(tmp_path, "global.dialogue.label.ok: Fine\n")
        with pytest.raises(MalformedTextKeyError, match=r"must name a panel"):
            LanguageManager(language_path)

    def test_a_rejected_file_leaves_the_held_text_in_place(self, tmp_path: Path) -> None:
        language_manager = LanguageManager(LANG_EN)
        language_path = write_language_file(tmp_path, "global.dialog.label: Fine\n")
        with pytest.raises(MalformedTextKeyError):
            language_manager.load(language_path)

        assert language_manager[OK_STRING_KEY] == "OK"

    def test_a_file_holding_no_mapping_is_rejected(self, tmp_path: Path) -> None:
        language_path = write_language_file(tmp_path, "- global.dialog.label.ok\n")
        with pytest.raises(TypeError):
            LanguageManager(language_path)
