from pathlib import Path

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
    TAG_INSTRUCTIONS_LIBRARY_THEME_GENERATOR,
    TAG_INSTRUCTIONS_LIBRARY_THEME_GROUP,
    TAG_INSTRUCTIONS_LIBRARY_THEME_INSTRUCTION,
    TAG_INSTRUCTIONS_LIBRARY_THEME_OUTDATED,
)
from sampletones_core.structures.tree import LibraryNode, NodeType, TreeNode
from sampletones_shared.paths.extensions import FileKind, file_kind


def directory_theme_tag(*, has_content: bool, has_favorite_ancestor: bool) -> str:
    """The theme of a folder's row that carries no star of its own."""
    if not has_content:
        return TAG_GLOBAL_THEME_FILE_NO_CONTENT

    if has_favorite_ancestor:
        return TAG_GLOBAL_THEME_FAVORITE_CHILD

    return TAG_GLOBAL_THEME_DEFAULT


def file_theme_tag(path: Path, *, has_favorite_ancestor: bool) -> str:
    """The theme of a file's row that carries no star of its own, which its kind decides."""
    match file_kind(path):
        case FileKind.RECONSTRUCTION:
            return TAG_GLOBAL_THEME_FILE_RECONSTRUCTION
        case FileKind.LIBRARY:
            return TAG_GLOBAL_THEME_FILE_LIBRARY
        case FileKind.AUDIO:
            return TAG_GLOBAL_THEME_FILE_WAVE
        case _:
            if has_favorite_ancestor:
                return TAG_GLOBAL_THEME_FAVORITE_CHILD
            return TAG_GLOBAL_THEME_DEFAULT


def library_theme_tag(node: TreeNode) -> str:
    """The theme of a row in a library's tree, which its node type decides."""
    match node.node_type:
        case NodeType.LIBRARY:
            if isinstance(node, LibraryNode) and node.outdated:
                return TAG_INSTRUCTIONS_LIBRARY_THEME_OUTDATED
            return TAG_INSTRUCTIONS_LIBRARY_THEME
        case NodeType.GENERATOR:
            return TAG_INSTRUCTIONS_LIBRARY_THEME_GENERATOR
        case NodeType.GROUP:
            return TAG_INSTRUCTIONS_LIBRARY_THEME_GROUP
        case NodeType.INSTRUCTION:
            return TAG_INSTRUCTIONS_LIBRARY_THEME_INSTRUCTION
        case _:
            return TAG_GLOBAL_THEME_DEFAULT
