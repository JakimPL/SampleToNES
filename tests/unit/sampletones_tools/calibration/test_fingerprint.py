import json
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
from sampletones_tools.calibration.corpus.truth import LINE, Truth
from sampletones_tools.calibration.fingerprint import (
    FINGERPRINT_FILE,
    ResumeRefusedError,
    RunFingerprint,
    check_resumable,
    fingerprint_of,
    measured_variants,
    write_fingerprint,
)
from sampletones_tools.calibration.referee.panel import RefereePanel
from sampletones_tools.calibration.variants import CalibrationVariant, build_variants
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .conversions import item_named, stub_panel
from .corpus.test_by_channel import CHORDS

CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.NOISE]
PITCH: Final[float] = 220.0


def _variants(method: SpectrumMethod) -> List[CalibrationVariant]:
    return build_variants(Config(), [method], [1.0], [], settings={}, levels=[WorkingLevel.DEFAULT])


@pytest.fixture(name="item")
def item_fixture() -> CorpusItem:
    return item_named("a", listed=True)


@pytest.fixture(name="panel")
def panel_fixture() -> RefereePanel:
    return stub_panel()


@pytest.fixture(name="fingerprint")
def fingerprint_fixture(item: CorpusItem, panel: RefereePanel) -> RunFingerprint:
    return fingerprint_of(_variants(SpectrumMethod.FFT), [item], CHANNELS, panel)


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
        TestCase(
            changed=replace(item_named("a", listed=True), channels=frozenset({ChannelName.TRIANGLE})),
            label="own channels",
        ),
        TestCase(
            changed=replace(item_named("a", listed=True), truth=Truth(instructions={}, pitches={LINE: (PITCH,)})),
            label="truth",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_sound_changed_reads_another_digest(
        self, test_case: TestCase, item: CorpusItem, panel: RefereePanel
    ) -> None:
        variants = _variants(SpectrumMethod.FFT)

        before = fingerprint_of(variants, [item], CHANNELS, panel)
        after = fingerprint_of(variants, [test_case.changed], CHANNELS, panel)

        assert before.items[item.name] != after.items[item.name]

    def test_a_truth_changed_in_one_frame_reads_another_digest(self, item: CorpusItem, panel: RefereePanel) -> None:
        variants = _variants(SpectrumMethod.FFT)
        held = replace(item, truth=Truth(instructions={}, pitches={LINE: (PITCH, PITCH)}))
        moved = replace(item, truth=Truth(instructions={}, pitches={LINE: (PITCH, None)}))

        before = fingerprint_of(variants, [held], CHANNELS, panel)
        after = fingerprint_of(variants, [moved], CHANNELS, panel)

        assert before.items[item.name] != after.items[item.name]

    def test_the_same_run_reads_the_same_fingerprint(self, fingerprint: RunFingerprint, panel: RefereePanel) -> None:
        same = fingerprint_of(_variants(SpectrumMethod.FFT), [item_named("a", listed=True)], CHANNELS, panel)

        assert same == fingerprint

    def test_a_sound_s_stems_setup_is_part_of_its_digest(self, panel: RefereePanel) -> None:
        (chord,) = build_chords(Config(), corpus=CHORDS)
        split = by_channel(chord, Config())
        assert split.stems is not None
        unsplit = replace(split, stems=None)

        variants = _variants(SpectrumMethod.FFT)

        assert fingerprint_of(variants, [split], CHANNELS, panel) != fingerprint_of(
            variants, [unsplit], CHANNELS, panel
        )

    def test_each_variant_is_held_by_its_label(self, fingerprint: RunFingerprint) -> None:
        assert list(fingerprint.variants) == [variant.label for variant in _variants(SpectrumMethod.FFT)]

    def test_channels_named_in_another_order_read_the_same_fingerprint(
        self, item: CorpusItem, panel: RefereePanel
    ) -> None:
        variants = _variants(SpectrumMethod.FFT)

        forward = fingerprint_of(variants, [item], CHANNELS, panel)
        backward = fingerprint_of(variants, [item], list(reversed(CHANNELS)), panel)

        assert forward == backward

    def test_the_referees_tuning_is_part_of_the_fingerprint(
        self, fingerprint: RunFingerprint, item: CorpusItem, panel: RefereePanel
    ) -> None:
        tuning = panel.config.model_copy(update={"volume_tolerance": panel.config.volume_tolerance + 1})

        retuned = fingerprint_of(_variants(SpectrumMethod.FFT), [item], CHANNELS, replace(panel, config=tuning))

        assert retuned.referees != fingerprint.referees

    def test_the_referees_judging_are_part_of_the_fingerprint(
        self, fingerprint: RunFingerprint, item: CorpusItem, panel: RefereePanel
    ) -> None:
        judged = fingerprint_of(_variants(SpectrumMethod.FFT), [item], CHANNELS, replace(panel, audio=()))

        assert judged.referees != fingerprint.referees


class TestCheckResumable:
    def test_a_run_measuring_alike_resumes(self, fingerprint: RunFingerprint, tmp_path: Path) -> None:
        write_fingerprint(tmp_path, fingerprint)

        check_resumable(tmp_path, fingerprint)

    def test_a_run_over_the_same_channels_named_in_another_order_resumes(
        self, fingerprint: RunFingerprint, item: CorpusItem, panel: RefereePanel, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint)

        check_resumable(tmp_path, fingerprint_of(_variants(SpectrumMethod.FFT), [item], CHANNELS[::-1], panel))

    def test_a_folder_without_a_run_is_refused(self, fingerprint: RunFingerprint, tmp_path: Path) -> None:
        with pytest.raises(ResumeRefusedError, match="holds no run"):
            check_resumable(tmp_path, fingerprint)

    def test_a_run_of_other_sounds_is_refused_naming_them(
        self, fingerprint: RunFingerprint, panel: RefereePanel, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint)
        other = fingerprint_of(_variants(SpectrumMethod.FFT), [item_named("a", listed=False)], CHANNELS, panel)

        with pytest.raises(ResumeRefusedError, match="measured other sounds;"):
            check_resumable(tmp_path, other)

    def test_a_run_over_other_channels_is_refused_naming_them(
        self, fingerprint: RunFingerprint, item: CorpusItem, panel: RefereePanel, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint)
        other = fingerprint_of(_variants(SpectrumMethod.FFT), [item], [ChannelName.PULSE1], panel)

        with pytest.raises(ResumeRefusedError, match="measured other channels;"):
            check_resumable(tmp_path, other)

    def test_a_run_judged_by_other_referees_is_refused_naming_them(
        self, fingerprint: RunFingerprint, item: CorpusItem, panel: RefereePanel, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint)
        other = fingerprint_of(_variants(SpectrumMethod.FFT), [item], CHANNELS, replace(panel, audio=()))

        with pytest.raises(ResumeRefusedError, match="measured other referees;"):
            check_resumable(tmp_path, other)

    def test_a_run_another_version_measured_is_refused_naming_it(
        self, fingerprint: RunFingerprint, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint.model_copy(update={"version": f"{fingerprint.version}.other"}))

        with pytest.raises(ResumeRefusedError, match="measured other program version;"):
            check_resumable(tmp_path, fingerprint)

    def test_every_part_measured_otherwise_is_named_in_the_stated_order(
        self, fingerprint: RunFingerprint, tmp_path: Path
    ) -> None:
        write_fingerprint(tmp_path, fingerprint)
        other = fingerprint_of(
            _variants(SpectrumMethod.CQT),
            [item_named("b", listed=True)],
            [ChannelName.NOISE],
            replace(stub_panel(), audio=()),
        ).model_copy(update={"version": f"{fingerprint.version}.other"})

        with pytest.raises(
            ResumeRefusedError, match="measured other variants, channels, sounds, referees, program version;"
        ):
            check_resumable(tmp_path, other)

    def test_a_fingerprint_an_earlier_version_wrote_is_refused_as_unreadable(
        self, fingerprint: RunFingerprint, tmp_path: Path
    ) -> None:
        earlier = fingerprint.model_dump(include={"variants", "channels", "items"})
        (tmp_path / FINGERPRINT_FILE).write_text(json.dumps(earlier), encoding="utf-8")

        with pytest.raises(ResumeRefusedError, match="in a form this version cannot read"):
            check_resumable(tmp_path, fingerprint)


class TestMeasuredVariants:
    def test_the_variants_read_back_in_the_order_the_run_measured_them(
        self, item: CorpusItem, panel: RefereePanel, tmp_path: Path
    ) -> None:
        methods = [SpectrumMethod.LOG_SPACED_FFT, SpectrumMethod.CQT, SpectrumMethod.FFT]
        variants = build_variants(Config(), methods, [1.0], [], settings={}, levels=[WorkingLevel.DEFAULT])
        write_fingerprint(tmp_path, fingerprint_of(variants, [item], CHANNELS, panel))

        assert measured_variants(tmp_path) == tuple(variant.label for variant in variants)

    def test_a_fingerprint_an_earlier_version_wrote_still_names_its_variants(
        self, fingerprint: RunFingerprint, tmp_path: Path
    ) -> None:
        earlier = fingerprint.model_dump(include={"variants", "channels", "items"})
        (tmp_path / FINGERPRINT_FILE).write_text(json.dumps(earlier), encoding="utf-8")

        assert measured_variants(tmp_path) == tuple(fingerprint.variants)

    def test_a_folder_without_a_run_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match=f"holds no {FINGERPRINT_FILE}"):
            measured_variants(tmp_path)
