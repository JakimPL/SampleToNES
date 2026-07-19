from typing import Tuple

import pytest

from sampletones_application.utils.file_dialogs.filter import FileFilter, normalize_extensions


@pytest.mark.parametrize(
    "extensions, expected",
    [
        ([".stp"], ("*.stp",)),
        (["*.stp"], ("*.stp",)),
        ([".wav", ".mp3"], ("*.wav", "*.mp3")),
        ((), ()),
    ],
)
def test_normalize_extensions(extensions: Tuple[str, ...], expected: Tuple[str, ...]) -> None:
    assert normalize_extensions(extensions) == expected


@pytest.mark.parametrize(
    "name, patterns, expected",
    [
        ("Project files", ("*.stp",), "Project files (*.stp)"),
        ("", ("*.stp",), "*.stp"),
        ("*.stp", ("*.stp",), "*.stp"),
        ("Audio files", ("*.wav", "*.mp3"), "Audio files (*.wav *.mp3)"),
    ],
)
def test_label(name: str, patterns: Tuple[str, ...], expected: str) -> None:
    assert FileFilter(name=name, patterns=patterns).label == expected
