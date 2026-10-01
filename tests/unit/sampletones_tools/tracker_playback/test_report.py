from dataclasses import replace
from typing import Final, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.project.project import Project
from sampletones_tools.tracker_playback.comparison import TraceComparison, compare_traces
from sampletones_tools.tracker_playback.outcome import ProjectOutcome
from sampletones_tools.tracker_playback.projects import CheckedProject
from sampletones_tools.tracker_playback.report import (
    COUNTED_DOWN,
    DIFFERS,
    DIFFERS_ONCE,
    LENGTHS_DIFFER,
    LONG_MODE,
    MATCHES,
    NOISE_SOUND,
    PULSE_SOUND,
    SHORT_MODE,
    SHORTENED,
    SILENT,
    SKIPPED_ROWS,
    TIMING_DIFFERS,
    TIMING_ONLY,
    TRIANGLE_SOUND,
    describe_sound,
    report_text,
    result_label,
)
from sampletones_tools.tracker_playback.trace.sound import ChannelSound, SongTrace, TickPosition
from tests.suite.playback import ReplayingTarget

EXAMPLES: Final[int] = 4
TONE: Final[ChannelSound] = ChannelSound(audible=True, period=427, volume=15, held=True, timbre=2)
QUIET: Final[ChannelSound] = replace(TONE, volume=5)
SILENT_SOUND: Final[ChannelSound] = ChannelSound(audible=False, period=0, volume=0, held=True, timbre=0)


def _trace(pulse: Tuple[ChannelSound, ...]) -> SongTrace:
    return SongTrace(
        positions=tuple(TickPosition(frame=0, row=tick) for tick in range(len(pulse))),
        channels={
            channel: pulse if channel == ChannelName.PULSE1 else (SILENT_SOUND,) * len(pulse)
            for channel in ChannelName.items()
        },
    )


def _outcome(name: str, comparison: TraceComparison) -> ProjectOutcome:
    return ProjectOutcome(
        project=CheckedProject(name=name, purpose=f"What {name} exercises.", project=Project.create()),
        comparison=comparison,
        skipped_rows=0,
        truncation=None,
    )


class TestDescribeSound:
    def test_a_silent_channel_reads_silent_on_any_channel(self) -> None:
        assert {describe_sound(channel, SILENT_SOUND) for channel in ChannelName.items()} == {SILENT}

    def test_each_channel_names_the_registers_it_has(self) -> None:
        short = ChannelSound(audible=True, period=9, volume=12, held=True, timbre=1)

        assert describe_sound(ChannelName.PULSE2, TONE) == PULSE_SOUND.format(period=427, volume=15, timbre=2)
        assert describe_sound(ChannelName.TRIANGLE, TONE) == TRIANGLE_SOUND.format(period=427)
        assert describe_sound(ChannelName.NOISE, short) == NOISE_SOUND.format(period=9, volume=12, mode=SHORT_MODE)
        assert describe_sound(ChannelName.NOISE, replace(short, timbre=0)) == NOISE_SOUND.format(
            period=9,
            volume=12,
            mode=LONG_MODE,
        )

    def test_a_sound_the_chip_counts_down_says_so_on_every_channel(self) -> None:
        counted_down = replace(TONE, held=False)

        for channel in ChannelName.items():
            assert describe_sound(channel, counted_down) == describe_sound(channel, TONE) + COUNTED_DOWN


class TestReportText:
    def test_the_summary_names_every_project_with_its_verdict(self, replaying_target: ReplayingTarget) -> None:
        alike = compare_traces(_trace((TONE, TONE)), _trace((TONE, TONE)), examples=EXAMPLES)
        different = compare_traces(_trace((TONE, TONE)), _trace((TONE, QUIET)), examples=EXAMPLES)

        text = report_text(replaying_target, (_outcome("alike", alike), _outcome("quiet", different)))

        assert replaying_target.title in text
        assert replaying_target.player in text
        assert f"| alike | 2 | 2 | {MATCHES} |" in text
        assert f"| quiet | 2 | 2 | {DIFFERS_ONCE} |" in text
        assert "What quiet exercises." in text

    def test_a_divergence_lists_both_sides_where_it_first_shows(self, replaying_target: ReplayingTarget) -> None:
        different = compare_traces(_trace((TONE, TONE)), _trace((TONE, QUIET)), examples=EXAMPLES)

        text = report_text(replaying_target, (_outcome("quiet", different),))

        application = describe_sound(ChannelName.PULSE1, TONE)
        engine = describe_sound(ChannelName.PULSE1, QUIET)
        assert f"| pulse1 | volume | 1 | 0 | 1 | {application} | {engine} | 1 |" in text

    def test_the_lengths_the_timing_and_what_the_export_left_out_are_stated(
        self, replaying_target: ReplayingTarget
    ) -> None:
        application = _trace((TONE, TONE))
        engine = SongTrace(positions=(TickPosition(frame=0, row=0),) * 3, channels=_trace((TONE,) * 3).channels)
        outcome = replace(
            _outcome("long", compare_traces(application, engine, examples=EXAMPLES)),
            skipped_rows=2,
            truncation=EnvelopeTruncation(frames=512, source_frames=601, instruments=1),
        )

        text = report_text(replaying_target, (outcome,))

        assert LENGTHS_DIFFER.format(application=2, engine=3) in text
        assert TIMING_DIFFERS.format(tick=1, frame=0, row=1, engine_frame=0, engine_row=0) in text
        assert SKIPPED_ROWS.format(count=2) in text
        assert SHORTENED.format(instruments=1, frames=512, source_frames=601) in text


class TestResultLabel:
    def test_a_project_differing_several_ways_counts_them(self) -> None:
        silent = replace(TONE, audible=False)
        comparison = compare_traces(_trace((TONE, TONE)), _trace((QUIET, silent)), examples=EXAMPLES)

        assert result_label(comparison) == DIFFERS.format(count=2)

    def test_a_project_whose_rows_alone_differ_says_so(self) -> None:
        comparison = compare_traces(_trace((TONE, TONE)), _trace((TONE, TONE, TONE)), examples=EXAMPLES)

        assert result_label(comparison) == TIMING_ONLY
