from pathlib import Path
from typing import Dict, Final, Tuple

import pytest

from sampletones_application.categories.elements.global_ import DialogElements
from sampletones_application.paths import LANG_EN
from sampletones_shared.meta.source.lookups import LookupSite
from sampletones_shared.meta.source.modules import source_paths
from sampletones_shared.meta.source.values import EnumTable
from tests.suite.scripts import load_script

check_language_keys = load_script("checks/language_keys.py")

ENUMS: Final[EnumTable] = check_language_keys.enum_table()

OK_KEY: Final[str] = "global.dialog.label.ok"
EXIT_KEY: Final[str] = "global.dialog.label.exit"
ABSENT_KEY: Final[str] = "global.dialog.label.absent"

LANGUAGE_FILE: Final[str] = f"""# =============================================================================
# Global — Dialog buttons
# =============================================================================
{OK_KEY}: "OK"
{EXIT_KEY}: "Exit"
"""

LOOKUP_SOURCE: Final[str] = (
    'def label(language_manager: LanguageManager) -> str:\n    return language_manager["{key}"]\n'
)


def lookup(
    values: Tuple[str, ...],
    exact: bool,
    unresolved: Tuple[str, ...] = (),
) -> LookupSite:
    return LookupSite(
        location="ui/panel.py:1",
        values=values,
        exact=exact,
        unresolved_parts=unresolved,
    )


def language_file(directory: Path, content: str) -> Path:
    path = directory / "en.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def source_tree(directory: Path, source: str) -> Path:
    root = directory / "src"
    root.mkdir()
    (root / "panel.py").write_text(source, encoding="utf-8")
    return root


class TestEnumTable:
    def test_the_hierarchy_states_its_pages(self) -> None:
        assert ENUMS["Page"]["GLOBAL"] == "global"

    def test_a_panel_taken_from_its_member_name_states_that_name(self) -> None:
        assert ENUMS["Panel"]["DIALOG"] == "dialog"

    def test_the_elements_package_states_its_members(self) -> None:
        assert ENUMS["DialogElements"]["OK"] == DialogElements.OK.value

    def test_every_element_enum_of_the_package_is_read(self) -> None:
        assert {
            "MenuElements",
            "SequencerTrackerElements",
            "InstructionsLibraryElements",
        }.issubset(ENUMS)

    def test_the_element_base_states_no_members(self) -> None:
        assert ENUMS[check_language_keys.ELEMENT_BASE] == {}


class TestLanguageEntries:
    def test_every_entry_is_read_with_its_line(self, tmp_path: Path) -> None:
        entries: Dict[str, int] = check_language_keys.language_entries(
            language_file(
                tmp_path,
                LANGUAGE_FILE,
            )
        )
        assert entries == {OK_KEY: 4, EXIT_KEY: 5}

    def test_a_comment_states_no_entry(self, tmp_path: Path) -> None:
        entries: Dict[str, int] = check_language_keys.language_entries(
            language_file(
                tmp_path,
                LANGUAGE_FILE,
            )
        )
        assert all(not key.startswith("#") for key in entries)

    def test_a_file_holding_no_mapping_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError):
            check_language_keys.language_entries(language_file(tmp_path, f"- {OK_KEY}\n"))


class TestBrokenLookups:
    def test_a_literal_key_outside_the_file_is_reported(self) -> None:
        findings = check_language_keys.broken_lookups([lookup((ABSENT_KEY,), True)], {OK_KEY: 1})

        assert len(findings) == 1
        assert findings[0].kind == check_language_keys.BROKEN_LOOKUP
        assert ABSENT_KEY in findings[0].message

    def test_a_literal_key_the_file_holds_is_no_finding(self) -> None:
        assert check_language_keys.broken_lookups([lookup((OK_KEY,), True)], {OK_KEY: 1}) == []

    def test_a_key_reached_through_an_enum_is_no_finding(self) -> None:
        assert check_language_keys.broken_lookups([lookup((ABSENT_KEY,), False)], {OK_KEY: 1}) == []


class TestUnresolvedLookups:
    def test_a_lookup_out_of_reach_is_reported_with_its_part(self) -> None:
        findings = check_language_keys.unresolved_lookups([lookup((), False, ("'element'",))])

        assert len(findings) == 1
        assert findings[0].kind == check_language_keys.UNRESOLVED_PART
        assert "'element'" in findings[0].message

    def test_a_lookup_out_of_reach_states_the_rule(self) -> None:
        findings = check_language_keys.unresolved_lookups([lookup((), False, ("'element'",))])
        assert check_language_keys.ELEMENT_BASE in findings[0].message

    def test_a_resolved_lookup_is_no_finding(self) -> None:
        assert check_language_keys.unresolved_lookups([lookup((OK_KEY,), True)]) == []


class TestUnreachedEntries:
    def test_an_entry_no_lookup_asks_for_is_reported_where_it_sits(self) -> None:
        findings = check_language_keys.unreached_entries(
            [lookup((OK_KEY,), True)],
            {OK_KEY: 4, EXIT_KEY: 5},
            Path("en.yaml"),
        )

        assert len(findings) == 1
        assert findings[0].kind == check_language_keys.UNREACHED_ENTRY
        assert findings[0].location == "en.yaml:5"
        assert EXIT_KEY in findings[0].message

    def test_an_entry_reached_through_an_enum_is_no_finding(self) -> None:
        findings = check_language_keys.unreached_entries(
            [lookup((OK_KEY, EXIT_KEY), False)],
            {OK_KEY: 4, EXIT_KEY: 5},
            Path("en.yaml"),
        )

        assert findings == []


class TestCheckLanguageKeys:
    def test_a_tree_asking_for_every_entry_reports_nothing(
        self,
        tmp_path: Path,
    ) -> None:
        source = source_tree(tmp_path, LOOKUP_SOURCE.format(key=OK_KEY))
        entries = language_file(tmp_path, f'{OK_KEY}: "OK"\n')

        assert check_language_keys.check_language_keys(source, entries) == []

    def test_a_key_the_file_omits_is_a_broken_lookup(
        self,
        tmp_path: Path,
    ) -> None:
        source = source_tree(tmp_path, LOOKUP_SOURCE.format(key=ABSENT_KEY))
        entries = language_file(tmp_path, f'{OK_KEY}: "OK"\n')

        kinds = [
            finding.kind
            for finding in check_language_keys.check_language_keys(
                source,
                entries,
            )
        ]

        assert kinds == [
            check_language_keys.BROKEN_LOOKUP,
            check_language_keys.UNREACHED_ENTRY,
        ]

    def test_an_entry_nobody_asks_for_is_unreached(
        self,
        tmp_path: Path,
    ) -> None:
        source = source_tree(tmp_path, LOOKUP_SOURCE.format(key=OK_KEY))
        entries = language_file(tmp_path, f'{OK_KEY}: "OK"\n{EXIT_KEY}: "Exit"\n')

        findings = check_language_keys.check_language_keys(source, entries)

        assert [finding.kind for finding in findings] == [check_language_keys.UNREACHED_ENTRY]
        assert findings[0].location.endswith("en.yaml:2")

    def test_a_dynamic_part_reaching_no_enum_is_unresolved(
        self,
        tmp_path: Path,
    ) -> None:
        source = source_tree(
            tmp_path,
            "def label(language_manager: LanguageManager, element: AbstractElement) -> str:\n"
            "    return language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, element]\n",
        )
        entries = language_file(tmp_path, f'{OK_KEY}: "OK"\n')

        kinds = [
            finding.kind
            for finding in check_language_keys.check_language_keys(
                source,
                entries,
            )
        ]

        assert check_language_keys.UNRESOLVED_PART in kinds

    def test_a_dynamic_part_of_a_concrete_enum_reaches_its_entries(
        self,
        tmp_path: Path,
    ) -> None:
        source = source_tree(
            tmp_path,
            "def label(language_manager: LanguageManager, element: DialogElements) -> str:\n"
            "    return language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, element]\n",
        )
        entries = language_file(tmp_path, f'{OK_KEY}: "OK"\n{EXIT_KEY}: "Exit"\n')

        assert check_language_keys.check_language_keys(source, entries) == []


class TestSweptRoots:
    """A root the sweep reads nothing under reports nothing, which reads as a clean tree."""

    def test_the_source_root_holds_modules(self) -> None:
        assert source_paths([check_language_keys.SOURCE_ROOT])

    def test_the_language_file_is_there_to_read(self) -> None:
        assert LANG_EN.is_file()


class TestMain:
    def test_the_repository_and_its_language_file_agree(self) -> None:
        assert check_language_keys.main([]) == 0

    def test_a_disagreement_is_reported_by_kind(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        source = source_tree(tmp_path, LOOKUP_SOURCE.format(key=ABSENT_KEY))
        entries = language_file(tmp_path, f'{OK_KEY}: "OK"\n')

        exit_code = check_language_keys.main(["--source", str(source), "--language-file", str(entries)])

        assert exit_code == 1
        error = capsys.readouterr().err
        assert f"[{check_language_keys.BROKEN_LOOKUP}] {source / 'panel.py'}:2" in error
        assert f"[{check_language_keys.UNREACHED_ENTRY}] {entries}:1" in error
