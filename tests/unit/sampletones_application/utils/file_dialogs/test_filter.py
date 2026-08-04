from typing import Optional, Tuple

import pytest

from sampletones_application.utils.file_dialogs.filter import (
    FileFilter,
    merge_filters,
    normalize_extensions,
)

FAMITRACKER_INSTRUMENT = FileFilter(name="FamiTracker instrument", patterns=("*.fti",))
BITPHASE_PRESET = FileFilter(name="Bitphase preset", patterns=("*.json",))


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


@pytest.mark.parametrize(
    "extensions, expected",
    [
        ([".fti"], (".fti",)),
        (["*.fti"], (".fti",)),
        ([".fti", ".btp", ".json"], (".fti", ".btp", ".json")),
    ],
)
def test_a_type_names_the_extensions_it_matches(
    extensions: Tuple[str, ...],
    expected: Tuple[str, ...],
) -> None:
    """The glob form belongs to the dialogs, so a caller reads plain extensions back out."""
    assert FileFilter.for_extensions("Instrument", extensions).extensions == expected


@pytest.mark.parametrize(
    "filters, expected",
    [
        ((), None),
        ((FAMITRACKER_INSTRUMENT,), FAMITRACKER_INSTRUMENT),
        (
            (FAMITRACKER_INSTRUMENT, BITPHASE_PRESET),
            FileFilter(name="FamiTracker instrument, Bitphase preset", patterns=("*.fti", "*.json")),
        ),
    ],
)
def test_merge_filters(
    filters: Tuple[FileFilter, ...],
    expected: Optional[FileFilter],
) -> None:
    assert merge_filters(filters) == expected


def test_merging_leaves_one_type_alone() -> None:
    """A lone type keeps its single pattern, which is the form a dialog fills the
    extension in for.
    """
    assert merge_filters((BITPHASE_PRESET,)).patterns == ("*.json",)


def test_merging_offers_a_shared_pattern_once() -> None:
    audio = FileFilter(name="Audio", patterns=("*.wav", "*.mp3"))
    wave = FileFilter(name="WAV audio", patterns=("*.wav",))
    assert merge_filters((audio, wave)).patterns == ("*.wav", "*.mp3")
