from dataclasses import replace
from pathlib import Path
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.nes import held, written_item
from sampletones_tools.calibration.layout import ORACLE_LABEL
from sampletones_tools.calibration.oracle.judging import oracle_rows
from sampletones_tools.calibration.oracle.reading import HIGHEST_READING, LOWEST_READING
from sampletones_tools.calibration.referee.panel import RefereePanel, build_panel
from sampletones_tools.calibration.referee.protocol import SCORE_READING
from sampletones_tools.calibration.renders import read_record, recording_path, variant_directory, write_record
from sampletones_tools.calibration.rows import CalibrationRow
from tests.suite.base import BaseTestSuite

SOUNDING: Final[int] = 20
SILENT: Final[int] = 4
TONE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=60, volume=12, duty_cycle=2)
HISS: Final[NoiseInstruction] = NoiseInstruction(on=True, period=4, volume=10, short=False)
SENTINEL: Final[float] = 123.0


@pytest.fixture(name="config", scope="module")
def config_fixture() -> Config:
    return Config()


@pytest.fixture(name="panel", scope="module")
def panel_fixture(config: Config) -> RefereePanel:
    return build_panel(config.library.sample_rate)


@pytest.fixture(name="written", scope="module")
def written_fixture(config: Config) -> CorpusItem:
    """A tone over hiss written as NES frames, which the page lists."""
    instructions: Dict[ChannelName, List[InstructionUnion]] = {
        ChannelName.PULSE1: held(ChannelName.PULSE1, TONE, sounding=SOUNDING, silent=SILENT),
        ChannelName.NOISE: held(ChannelName.NOISE, HISS, sounding=SOUNDING, silent=SILENT),
    }
    return written_item(
        "tone-over-hiss", Family.SEQUENCES, "sequences-mixed", listed=True, instructions=instructions, config=config
    )


@pytest.fixture(name="recorded")
def recorded_fixture(written: CorpusItem) -> CorpusItem:
    """A sound the corpus knows no frames of, as a recording's truth is."""
    return replace(written, name="recorded", truth=None)


def _readings(rows: List[CalibrationRow]) -> Dict[Tuple[str, str], float]:
    return {(row.referee, row.component): row.score for row in rows}


class TestOracleRows(BaseTestSuite):
    """The oracle reads every sound written as NES frames, from several starts of its channels."""

    def test_a_written_sound_is_read_by_every_audio_referee_within_its_spread(
        self, tmp_path: Path, written: CorpusItem, panel: RefereePanel, config: Config
    ) -> None:
        readings = _readings(oracle_rows([written], panel, tmp_path, config, resume=False))

        for referee in panel.audio:
            low, mean, high = (
                readings[(referee.name, part)] for part in (LOWEST_READING, SCORE_READING, HIGHEST_READING)
            )
            assert low <= mean <= high

    def test_the_noise_s_starts_spread_the_oracle_s_score(
        self, tmp_path: Path, written: CorpusItem, panel: RefereePanel, config: Config
    ) -> None:
        readings = _readings(oracle_rows([written], panel, tmp_path, config, resume=False))

        headline = panel.audio[0].name
        assert readings[(headline, LOWEST_READING)] < readings[(headline, HIGHEST_READING)]

    def test_a_sound_written_otherwise_is_left_unread(
        self, tmp_path: Path, recorded: CorpusItem, panel: RefereePanel, config: Config
    ) -> None:
        assert not oracle_rows([recorded], panel, tmp_path, config, resume=False)
        assert read_record(tmp_path, ORACLE_LABEL, recorded.name) is None

    def test_a_sound_reads_alike_in_every_run(
        self, tmp_path: Path, written: CorpusItem, panel: RefereePanel, config: Config
    ) -> None:
        first = oracle_rows([written], panel, tmp_path / "first", config, resume=False)
        second = oracle_rows([written], panel, tmp_path / "second", config, resume=False)

        assert first == second

    def test_the_record_stands_at_the_true_level_with_the_channels_the_frames_sound(
        self, tmp_path: Path, written: CorpusItem, panel: RefereePanel, config: Config
    ) -> None:
        oracle_rows([written], panel, tmp_path, config, resume=False)

        record = read_record(tmp_path, ORACLE_LABEL, written.name)
        assert record is not None
        assert record.level == VariantLevel.TRUE
        assert record.timelines == {
            ChannelName.PULSE1.value: "1" * SOUNDING + "0" * SILENT,
            ChannelName.NOISE.value: "1" * SOUNDING + "0" * SILENT,
        }

    def test_a_listed_sound_s_render_parts_and_recording_are_written_for_the_page(
        self, tmp_path: Path, written: CorpusItem, panel: RefereePanel, config: Config
    ) -> None:
        oracle_rows([written], panel, tmp_path, config, resume=False)

        assert (variant_directory(tmp_path, ORACLE_LABEL) / f"{written.name}.flac").is_file()
        assert (variant_directory(tmp_path, ORACLE_LABEL) / written.name / "pulse1.flac").is_file()
        assert recording_path(tmp_path, VariantLevel.TRUE, written.name).is_file()

    def test_a_resumed_run_takes_the_record_an_oracle_left(
        self, tmp_path: Path, written: CorpusItem, panel: RefereePanel, config: Config
    ) -> None:
        oracle_rows([written], panel, tmp_path, config, resume=False)
        record = read_record(tmp_path, ORACLE_LABEL, written.name)
        assert record is not None
        headline = panel.audio[0].name
        write_record(
            tmp_path,
            record.model_copy(update={"judgments": {**record.judgments, headline: {SCORE_READING: SENTINEL}}}),
        )

        readings = _readings(oracle_rows([written], panel, tmp_path, config, resume=True))

        assert readings[(headline, SCORE_READING)] == SENTINEL
