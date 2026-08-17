from pathlib import Path
from typing import Dict, Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.reconstruction.browser.manager import BrowserManager
from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.reconstruction import (
    ReconstructionEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
    ScanEntry,
)
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.paths import EXT_FILE_RECONSTRUCTION
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import FileSystemNode, NodeType, TreeNode
from tests.suite.language import FakeLanguageManager

HASH_A: Final[str] = "6edf7c948606917a78b45d153c7ca7e0"
HASH_B: Final[str] = "a1b2c3d4e5f60718293a4b5c6d7e8f90"

RECONSTRUCTIONS: Final[Path] = Path("/reconstructions")
BRANCH_NAME: Final[str] = "branch"

CONFIGURATION_BRANCH_KEY: Final[str] = "global.browser.label.reconstructions"
SAMPLE_BRANCH_KEY: Final[str] = "global.browser.label.samples"


def config_fields(
    *,
    sample_rate: int = 44100,
    nes_frequency: int = 30,
    spectrum_method: SpectrumMethod = SpectrumMethod.FFT,
    transformation_gamma: int = 0,
    generators: str = "PTN",
    config_hash: str = HASH_A,
) -> ConfigDirectoryFields:
    """Builds configuration fields, so a test states only the field whose effect it examines."""
    return ConfigDirectoryFields(
        sr=sample_rate,
        nf=nes_frequency,
        sm=spectrum_method,
        tg=transformation_gamma,
        gn=generators,
        ch=config_hash,
    )


def reconstruction_entry(directory: Path, *relative_parts: str) -> ReconstructionEntry:
    return ReconstructionEntry(path=directory.joinpath(*relative_parts).with_suffix(EXT_FILE_RECONSTRUCTION))


def config_entry(fields: ConfigDirectoryFields, *audio_names: str) -> DirectoryEntry:
    """Records a configuration directory holding one reconstruction per stated audio name."""
    directory = RECONSTRUCTIONS / fields.directory_name
    return DirectoryEntry(
        path=directory,
        config=fields,
        entries=tuple(reconstruction_entry(directory, name) for name in audio_names),
    )


def plain_entry(name: str, *entries: ScanEntry) -> DirectoryEntry:
    """Records a folder whose name states no configuration."""
    return DirectoryEntry(path=RECONSTRUCTIONS / name, config=None, entries=entries)


def scan_of(*entries: ScanEntry) -> ReconstructionScan:
    return ReconstructionScan(entries=entries)


def config_directory(root: Path, fields: ConfigDirectoryFields) -> Path:
    directory = root / fields.directory_name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_reconstruction(directory: Path, *relative_parts: str) -> Path:
    """Creates an empty reconstruction file at the stated place, with the folders leading to it."""
    path = directory.joinpath(*relative_parts).with_suffix(EXT_FILE_RECONSTRUCTION)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def directory_children(node: TreeNode) -> Dict[str, FileSystemNode]:
    return {
        child.name: child
        for child in node.children
        if isinstance(child, FileSystemNode) and child.node_type == NodeType.DIRECTORY
    }


def file_children(node: TreeNode) -> Dict[str, FileSystemNode]:
    return {
        child.name: child
        for child in node.children
        if isinstance(child, FileSystemNode) and child.node_type == NodeType.FILE
    }


def group_children(node: TreeNode) -> Dict[str, TreeNode]:
    return {child.name: child for child in node.children if child.node_type == NodeType.GROUP}


def sample_children(node: TreeNode) -> Dict[str, TreeNode]:
    return {child.name: child for child in node.children if child.node_type == NodeType.SAMPLE}


def branch_of(browser_manager: BrowserManager, key: str) -> TreeNode:
    root = browser_manager.tree.get_root()
    assert root is not None
    return group_children(root)[key]


def configuration_branch(browser_manager: BrowserManager) -> TreeNode:
    return branch_of(browser_manager, CONFIGURATION_BRANCH_KEY)


def sample_branch(browser_manager: BrowserManager) -> TreeNode:
    return branch_of(browser_manager, SAMPLE_BRANCH_KEY)


@pytest.fixture
def config_manager(tmp_path: Path) -> MagicMock:
    mock = MagicMock()
    mock.get_reconstructions_directory.return_value = tmp_path
    return mock


@pytest.fixture
def browser_manager(config_manager: MagicMock) -> BrowserManager:
    return BrowserManager(config_manager, language_manager=FakeLanguageManager())  # type: ignore[arg-type]
