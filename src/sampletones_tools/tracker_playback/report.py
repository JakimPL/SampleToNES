from typing import Final, List, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_shared.utils.tables import Table
from sampletones_tools.tracker_playback.comparison import (
    Divergence,
    DivergentTick,
    TimingDivergence,
    TraceComparison,
)
from sampletones_tools.tracker_playback.outcome import ProjectOutcome
from sampletones_tools.tracker_playback.targets.protocol import PlaybackTarget
from sampletones_tools.tracker_playback.trace.sound import ChannelSound

TITLE: Final[str] = "# What {tracker} plays of the corpus"
INTRODUCTION: Final[str] = (
    "Each project was exported to {tracker} with the application's own exporter and played by {player}. Every "
    "engine tick of every channel is held against what the application plays, both read as the registers the "
    "console takes. A channel that is silent on both sides counts as alike."
)
SUMMARY_COLUMNS: Final[Tuple[str, ...]] = ("Project", "Ticks in the app", "Ticks in the tracker", "Result")
DIVERGENCE_COLUMNS: Final[Tuple[str, ...]] = (
    "Channel",
    "Differs in",
    "Tick",
    "Frame",
    "Row",
    "Application",
    "Tracker",
    "Ticks",
)
MATCHES: Final[str] = "matches"
DIFFERS_ONCE: Final[str] = "1 difference"
TIMING_ONLY: Final[str] = "the rows or the length differ"
DIFFERS: Final[str] = "{count} differences"
LENGTHS_DIFFER: Final[str] = "The application plays {application} ticks and the tracker plays {engine}."
TIMING_DIFFERS: Final[str] = (
    "The rows part at tick {tick}: the application is at frame {frame}, row {row}, "
    "and the tracker at frame {engine_frame}, row {engine_row}."
)
ALL_ALIKE: Final[str] = "Every tick sounds alike."
SKIPPED_ROWS: Final[str] = "Rows the export wrote as note cuts, for lack of an instrument on their channel: {count}."
SHORTENED: Final[str] = (
    "Instruments the export shortened to {frames} of their {source_frames} frames, "
    "the most the format holds: {instruments}."
)
SILENT: Final[str] = "silent"
PULSE_SOUND: Final[str] = "timer {period}, volume {volume}, duty {timbre}"
TRIANGLE_SOUND: Final[str] = "timer {period}"
NOISE_SOUND: Final[str] = "period {period}, volume {volume}, {mode}"
SHORT_MODE: Final[str] = "short"
LONG_MODE: Final[str] = "long"
FIELD_SEPARATOR: Final[str] = ", "
CONTINUED: Final[str] = ""


def describe_sound(
    channel: ChannelName,
    sound: ChannelSound,
) -> str:
    """One channel's sound on a tick, in the registers a reader looks for on that channel.

    Args:
        channel: The channel sounding.
        sound: What it sounds.

    Returns:
        str: The sound, or that the channel is silent.
    """
    if not sound.audible:
        return SILENT

    match channel:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            return PULSE_SOUND.format(
                period=sound.period,
                volume=sound.volume,
                timbre=sound.timbre,
            )
        case ChannelName.TRIANGLE:
            return TRIANGLE_SOUND.format(period=sound.period)
        case ChannelName.NOISE:
            mode = SHORT_MODE if sound.timbre else LONG_MODE
            return NOISE_SOUND.format(
                period=sound.period,
                volume=sound.volume,
                mode=mode,
            )


def result_label(comparison: TraceComparison) -> str:
    """The verdict a project's line in the summary carries: a match, or how many ways it differs."""
    if comparison.matches:
        return MATCHES

    count = len(comparison.divergences)
    match count:
        case 0:
            return TIMING_ONLY
        case 1:
            return DIFFERS_ONCE
        case _:
            return DIFFERS.format(count=count)


def divergence_table(divergences: Sequence[Divergence]) -> Table:
    """The table listing every way a project's channels sound differently, a line per example.

    A divergence's first line names the channel, the fields and how many ticks it strikes, and the
    lines under it carry its further examples alone.
    """
    return Table(
        columns=DIVERGENCE_COLUMNS,
        rows=tuple(
            divergence_row(divergence, example, opening=index == 0)
            for divergence in divergences
            for index, example in enumerate(divergence.examples)
        ),
    )


def divergence_row(
    divergence: Divergence,
    example: DivergentTick,
    *,
    opening: bool,
) -> Tuple[str, ...]:
    """One line of the divergence table: an example, under the divergence it belongs to where it opens it."""
    return (
        divergence.channel.value if opening else CONTINUED,
        FIELD_SEPARATOR.join(field.value for field in divergence.fields) if opening else CONTINUED,
        str(example.tick),
        str(example.position.frame),
        str(example.position.row),
        describe_sound(divergence.channel, example.application),
        describe_sound(divergence.channel, example.engine),
        str(divergence.ticks) if opening else CONTINUED,
    )


def timing_line(timing: TimingDivergence) -> str:
    """Where the two players first place a tick at different rows."""
    return TIMING_DIFFERS.format(
        tick=timing.tick,
        frame=timing.position.frame,
        row=timing.position.row,
        engine_frame=timing.engine_position.frame,
        engine_row=timing.engine_position.row,
    )


def export_notes(outcome: ProjectOutcome) -> List[str]:
    """What the export itself reported leaving out, which accounts for a difference it expects.

    Args:
        outcome: How the project fared.

    Returns:
        List[str]: One line per thing left out.
    """
    notes: List[str] = []
    if outcome.skipped_rows:
        notes.append(SKIPPED_ROWS.format(count=outcome.skipped_rows))

    truncation = outcome.truncation
    if truncation is not None:
        notes.append(
            SHORTENED.format(
                instruments=truncation.instruments,
                frames=truncation.frames,
                source_frames=truncation.source_frames,
            )
        )

    return notes


def project_section(outcome: ProjectOutcome) -> List[str]:
    """The report's section on one project: what it exercises, what the export left out, and every difference.

    Args:
        outcome: How the project fared.

    Returns:
        List[str]: The section's lines.
    """
    comparison = outcome.comparison
    lines = [f"## {outcome.project.name}", "", outcome.project.purpose, ""]
    lines.extend(line for note in export_notes(outcome) for line in (note, ""))
    if comparison.application_ticks != comparison.engine_ticks:
        lines.extend(
            (
                LENGTHS_DIFFER.format(
                    application=comparison.application_ticks,
                    engine=comparison.engine_ticks,
                ),
                "",
            )
        )

    if comparison.timing is not None:
        lines.extend((timing_line(comparison.timing), ""))

    if comparison.divergences:
        lines.extend(divergence_table(comparison.divergences).markdown_lines())
        lines.append("")
    elif comparison.matches:
        lines.extend((ALL_ALIKE, ""))

    return lines


def summary_table(outcomes: Sequence[ProjectOutcome]) -> Table:
    """The table naming every project with its tick counts and its verdict."""
    return Table(
        columns=SUMMARY_COLUMNS,
        rows=tuple(
            (
                outcome.project.name,
                str(outcome.comparison.application_ticks),
                str(outcome.comparison.engine_ticks),
                result_label(outcome.comparison),
            )
            for outcome in outcomes
        ),
    )


def report_text(
    target: PlaybackTarget,
    outcomes: Sequence[ProjectOutcome],
) -> str:
    """The whole report: the summary first, then a section per project.

    Args:
        target: The tracker that played the projects.
        outcomes: How each project fared, in the order they were played.

    Returns:
        str: The report as Markdown.
    """
    lines = [
        TITLE.format(tracker=target.title),
        "",
        INTRODUCTION.format(
            tracker=target.title,
            player=target.player,
        ),
        "",
    ]
    lines.extend(summary_table(outcomes).markdown_lines())
    lines.append("")
    for outcome in outcomes:
        lines.extend(project_section(outcome))

    return "\n".join(lines)
