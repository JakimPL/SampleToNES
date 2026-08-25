from pathlib import Path
from typing import Dict, Final, List

import pytest

from sampletones_shared.meta.source.modules import SourceModule, source_paths
from sampletones_shared.paths.source import SOURCE_ROOT
from tests.suite.scripts import load_script
from tests.suite.source import parse_source

check_unused_tags = load_script("checks/unused_tags.py")

TAGS_MODULE: Final[Path] = Path("tags/general.py")
PANEL_MODULE: Final[Path] = Path("ui/panel.py")

TAGS_SOURCE: Final[str] = """
TAG_GLOBAL_WINDOW_MAIN = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.WINDOW, "main")
SUF_BUTTON = "button"
SUF_BUTTON_COPY = compose_tag(SUF_BUTTON, "copy")
PRE_RECONSTRUCTION_CHANNEL = "channel"
PANEL_WIDTH = 320
"""

PANEL_SOURCE: Final[str] = """
from tags.general import PRE_RECONSTRUCTION_CHANNEL, SUF_BUTTON_COPY, TAG_GLOBAL_WINDOW_MAIN

def build() -> None:
    show(TAG_GLOBAL_WINDOW_MAIN, SUF_BUTTON_COPY)
"""


def module(path: Path, source: str) -> SourceModule:
    return SourceModule(path=path, tree=parse_source(source))


def fragment_names(source: str) -> List[str]:
    return [fragment.name for fragment in check_unused_tags.declared_fragments([module(TAGS_MODULE, source)])]


def unread(tags_source: str, panel_source: str) -> List[str]:
    tags = [module(TAGS_MODULE, tags_source)]
    fragments = check_unused_tags.declared_fragments(tags)
    counts = check_unused_tags.reference_counts([*tags, module(PANEL_MODULE, panel_source)])
    return [fragment.name for fragment in check_unused_tags.unread_fragments(fragments, counts)]


class TestDeclaredFragments:
    def test_a_tag_is_a_fragment(self) -> None:
        assert "TAG_GLOBAL_WINDOW_MAIN" in fragment_names(TAGS_SOURCE)

    def test_a_suffix_is_a_fragment(self) -> None:
        assert {"SUF_BUTTON", "SUF_BUTTON_COPY"}.issubset(fragment_names(TAGS_SOURCE))

    def test_a_prefix_is_a_fragment(self) -> None:
        assert "PRE_RECONSTRUCTION_CHANNEL" in fragment_names(TAGS_SOURCE)

    def test_a_constant_of_another_kind_is_no_fragment(self) -> None:
        assert "PANEL_WIDTH" not in fragment_names(TAGS_SOURCE)

    def test_a_fragment_carries_where_it_is_declared(self) -> None:
        declared = check_unused_tags.declared_fragments([module(TAGS_MODULE, TAGS_SOURCE)])
        assert declared[0].location == f"{TAGS_MODULE}:2"


class TestReferenceCounts:
    def test_a_read_raises_the_count(self) -> None:
        counts: Dict[str, int] = check_unused_tags.reference_counts([module(PANEL_MODULE, PANEL_SOURCE)])
        assert counts["TAG_GLOBAL_WINDOW_MAIN"] == 1

    def test_an_import_alone_raises_no_count(self) -> None:
        counts: Dict[str, int] = check_unused_tags.reference_counts([module(PANEL_MODULE, PANEL_SOURCE)])
        assert "PRE_RECONSTRUCTION_CHANNEL" not in counts


class TestUnreadFragments:
    def test_a_fragment_nobody_reads_is_reported(self) -> None:
        assert unread(TAGS_SOURCE, PANEL_SOURCE) == ["PRE_RECONSTRUCTION_CHANNEL"]

    def test_a_fragment_feeding_another_fragment_counts_as_read(self) -> None:
        assert "SUF_BUTTON" not in unread(TAGS_SOURCE, PANEL_SOURCE)

    def test_a_fragment_read_in_the_sources_counts_as_read(self) -> None:
        assert "SUF_BUTTON_COPY" not in unread(TAGS_SOURCE, PANEL_SOURCE)

    def test_a_tree_reading_every_fragment_reports_nothing(self) -> None:
        panel = PANEL_SOURCE.replace("SUF_BUTTON_COPY)", "SUF_BUTTON_COPY, PRE_RECONSTRUCTION_CHANNEL)")
        assert unread(TAGS_SOURCE, panel) == []


class TestSweptRoots:
    """A root the sweep reads nothing under reports nothing, which reads as a clean tree."""

    def test_the_tags_package_holds_modules(self) -> None:
        assert source_paths([check_unused_tags.TAGS_PACKAGE])

    def test_every_reference_root_holds_modules(self) -> None:
        assert all(source_paths([root]) for root in check_unused_tags.REFERENCE_ROOTS)

    def test_the_tags_package_sits_under_the_source_root(self) -> None:
        assert SOURCE_ROOT in check_unused_tags.TAGS_PACKAGE.parents


class TestMain:
    def test_the_repository_reads_every_fragment_it_declares(self) -> None:
        assert check_unused_tags.main([]) == 0

    def test_an_unread_fragment_is_reported_where_it_sits(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tags = tmp_path / "tags"
        tags.mkdir()
        (tags / "general.py").write_text('TAG_READ = "read"\nSUF_UNREAD = "unread"\n', encoding="utf-8")
        sources = tmp_path / "ui"
        sources.mkdir()
        (sources / "panel.py").write_text("show(TAG_READ)\n", encoding="utf-8")

        exit_code = check_unused_tags.main(["--tags", str(tags), "--reference-root", str(sources)])

        assert exit_code == 1
        error = capsys.readouterr().err
        assert "SUF_UNREAD" in error
        assert f"{tags / 'general.py'}:2" in error
        assert "TAG_READ" not in error
