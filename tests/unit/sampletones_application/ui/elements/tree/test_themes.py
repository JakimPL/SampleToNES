from pathlib import Path
from typing import Final

import pytest

from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_FAVORITE_CHILD,
    TAG_GLOBAL_THEME_FILE_LIBRARY,
    TAG_GLOBAL_THEME_FILE_NO_CONTENT,
    TAG_GLOBAL_THEME_FILE_RECONSTRUCTION,
    TAG_GLOBAL_THEME_FILE_WAVE,
)
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_THEME,
    TAG_INSTRUCTIONS_LIBRARY_THEME_OUTDATED,
)
from sampletones_application.ui.elements.tree.themes import directory_theme_tag, file_theme_tag, library_theme_tag
from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.library.settings import LibrarySettings
from sampletones_core.structures.tree import LibraryNode, NodeType, TreeNode
from sampletones_shared.paths.extensions import EXT_FILE_LIBRARY, EXT_FILE_RECONSTRUCTION

LIBRARY_KEY: Final[InstructionLibraryKey] = InstructionLibraryKey.create(
    LibrarySettings.of(Config()), Window.from_config(Config())
)


class TestAFolderRow:
    def test_an_empty_folder_reads_as_empty_even_inside_a_starred_folder(self) -> None:
        assert directory_theme_tag(has_content=False, has_favorite_ancestor=True) == TAG_GLOBAL_THEME_FILE_NO_CONTENT

    @pytest.mark.parametrize(
        ("has_favorite_ancestor", "theme"),
        [(True, TAG_GLOBAL_THEME_FAVORITE_CHILD), (False, TAG_GLOBAL_THEME_DEFAULT)],
    )
    def test_a_folder_with_content_reads_by_its_ancestry(self, has_favorite_ancestor: bool, theme: str) -> None:
        assert directory_theme_tag(has_content=True, has_favorite_ancestor=has_favorite_ancestor) == theme


class TestAFileRow:
    @pytest.mark.parametrize(
        ("name", "theme"),
        [
            (f"song{EXT_FILE_RECONSTRUCTION}", TAG_GLOBAL_THEME_FILE_RECONSTRUCTION),
            (f"song{EXT_FILE_RECONSTRUCTION.upper()}", TAG_GLOBAL_THEME_FILE_RECONSTRUCTION),
            (f"pulse{EXT_FILE_LIBRARY}", TAG_GLOBAL_THEME_FILE_LIBRARY),
            ("kick.WAV", TAG_GLOBAL_THEME_FILE_WAVE),
        ],
    )
    def test_a_file_of_a_known_kind_reads_by_its_kind_inside_a_starred_folder(self, name: str, theme: str) -> None:
        assert file_theme_tag(Path("/songs") / name, has_favorite_ancestor=True) == theme

    @pytest.mark.parametrize("name", ["notes.txt", "README", ".wav.bak"])
    def test_a_file_of_another_kind_reads_by_its_ancestry(self, name: str) -> None:
        path = Path("/songs") / name
        assert (
            file_theme_tag(path, has_favorite_ancestor=True),
            file_theme_tag(path, has_favorite_ancestor=False),
        ) == (TAG_GLOBAL_THEME_FAVORITE_CHILD, TAG_GLOBAL_THEME_DEFAULT)


class TestALibraryTreeRow:
    @pytest.mark.parametrize(
        ("outdated", "theme"),
        [(True, TAG_INSTRUCTIONS_LIBRARY_THEME_OUTDATED), (False, TAG_INSTRUCTIONS_LIBRARY_THEME)],
    )
    def test_a_library_reads_by_whether_it_is_outdated(self, outdated: bool, theme: str) -> None:
        node = LibraryNode("pulse", LIBRARY_KEY, outdated=outdated)
        assert library_theme_tag(node) == theme

    def test_a_library_row_carrying_no_library_reads_as_a_current_one(self) -> None:
        assert library_theme_tag(TreeNode("pulse", NodeType.LIBRARY)) == TAG_INSTRUCTIONS_LIBRARY_THEME

    @pytest.mark.parametrize("node_type", [NodeType.FILE, NodeType.DIRECTORY, NodeType.SAMPLE])
    def test_a_row_of_another_kind_reads_as_the_default(self, node_type: NodeType) -> None:
        assert library_theme_tag(TreeNode("row", node_type)) == TAG_GLOBAL_THEME_DEFAULT
