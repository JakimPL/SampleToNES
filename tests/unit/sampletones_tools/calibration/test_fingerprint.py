from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.corpus.by_channel import by_channel
from sampletones_tools.calibration.corpus.chords import build_chords
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.fingerprint import (
    ResumeRefusedError,
    RunFingerprint,
    check_resumable,
    fingerprint_of,
    write_fingerprint,
)
from sampletones_tools.calibration.variants import CalibrationVariant, build_variants
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .conversions import item_named
from .corpus.test_by_channel import CHORDS

CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.NOISE]


def _variants(method: SpectrumMethod) -> List[CalibrationVariant]:
    return build_variants(Config(), [method], [1.0], [], settings={}, levels=[WorkingLevel.DEFAULT])


@pytest.fixture(name="item")
def item_fixture() -> CorpusItem:
    return item_named("a", listed=True)


@pytest.fixture(name="fingerprint")
def fingerprint_fixture(item: CorpusItem) -> RunFingerprint:
    return fingerprint_of(_variants(SpectrumMethod.FFT), [item], CHANNELS)


class TestFingerprintOf(BaseTestSuite):
    """A sound's digest tells apart every change a record depends on."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        changed: CorpusItem

    test_cases = (
        TestCase(changed=replace(item_named("a", listed=True), listed=False), label="listing"),
        TestCase(changed=replace(item_named("a", listed=True), family=Family.CHORDS), label="family"),
        TestCase(changed=replace(item_named("a", listed=True), category="notes-noise"), label="category"),
        TestCase(changed=replace(item_named("a", listed=True), audio=np.ones(1)), label="audio"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_sound_changed_reads_another_digest(self, test_case: TestCase, item: CorpusItem) -> None:
        variants = _variants(SpectrumMethod.FFT)

        before = fingerprint_of(variants, [item], CHANNELS)
        after = fingerprint_of(variants, [test_case.changed], CHANNELS)

        assert before.items[item.name] != after.items[item.name]

    def test_the_same_run_reads_the_same_fingerprint(self, fingerprint: RunFingerprint) -> None:
        assert fingerprint_of(_variants(SpectrumMethod.FFT), [item_named("a", listed=True)], CHANNELS) == fingerprint

    def test_a_sound_s_stems_setup_is_part_of_its_digest(self) -> None:
        (chord,) = build_chords(Config(), corpus=CHORDS)
        split = by_channel(chord, Config())
        assert split.stems is not None
        unsplit = replace(split, stems=None)

        variants = _variants(SpectrumMethod.FFT)

        assert fingerprint_of(variants, [split], CHANNELS) != fingerprint_of(variants, [unsplit], CHANNELS)

    def test_each_variant_is_held_by_its_label(self, fingerprint: RunFingerprint) -> None:
        assert list(fingerprint.variants) == [variant.label for variant in _variants(SpectrumMethod.FFT)]


class TestCheckResumable:
    def test_a_run_measuring_alike_resumes(self, fingerprint: RunFingerprint, tmp_path: Path) -> None:
        write_fingerprint(tmp_path, fingerprint)

        check_resumable(tmp_path, fingerprint)

    def test_a_folder_without_a_run_is_refused(self, fingerprint: RunFingerprint, tmp_path: Path) -> None:
        with pytest.raises(ResumeRefusedError, match="holds no run"):
            check_resumable(tmp_path, fingerprint)

    def test_a_run_of_other_sounds_is_refused_naming_them(self, fingerprint: RunFingerprint, tmp_path: Path) -> None:
        write_fingerprint(tmp_path, fingerprint)
        other = fingerprint_of(_variants(SpectrumMethod.FFT), [item_named("a", listed=False)], CHANNELS)

        with pytest.raises(ResumeRefusedError, match="measured other sounds;"):
            check_resumable(tmp_path, other)

    def test_a_run_over_other_channels_is_refused_naming_them(
        self, fingerprint: RunFingerprint, item: CorpusItem, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint)
        other = fingerprint_of(_variants(SpectrumMethod.FFT), [item], [ChannelName.PULSE1])

        with pytest.raises(ResumeRefusedError, match="measured other channels;"):
            check_resumable(tmp_path, other)

    def test_every_part_measured_otherwise_is_named_in_a_fixed_order(
        self, fingerprint: RunFingerprint, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint)
        other = fingerprint_of(_variants(SpectrumMethod.CQT), [item_named("b", listed=True)], [ChannelName.NOISE])

        with pytest.raises(ResumeRefusedError, match="measured other variants, channels, sounds;"):
            check_resumable(tmp_path, other)
