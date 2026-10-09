from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Dict, List, Optional, Self, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.tracker_playback.trace.sound import ChannelSound, SongTrace, TickPosition


class SoundField(StrEnum):
    AUDIBLE = "audible"
    PERIOD = "period"
    VOLUME = "volume"
    TIMBRE = "timbre"


@dataclass(frozen=True)
class DivergentTick:
    """One tick a channel sounds differently on, with what each side sounds.

    Attributes:
        tick: The tick, counted from the song's first.
        position: Where the application places the tick.
        application: What the application sounds.
        engine: What the tracker sounds.
    """

    tick: int
    position: TickPosition
    application: ChannelSound
    engine: ChannelSound


@dataclass(frozen=True)
class Divergence:
    """One way a channel sounds differently in the tracker, from the first tick it shows onward.

    Ticks that differ in the same fields of the same channel share one divergence, so each field a
    cause strikes is reported once with how often it strikes. Two causes striking the same field,
    such as a pitch off by a step and a transpose left out, show apart in the examples: a tick joins
    them where it opens a row the examples have yet to reach and the two sides sound values the last
    example lacks.

    Attributes:
        channel: The channel that sounds differently.
        fields: What differs: whether it sounds at all, or which of its registers.
        examples: The first tick it shows on, then the ticks that change what the sides sound.
        ticks: How many ticks show the same difference.
    """

    channel: ChannelName
    fields: Tuple[SoundField, ...]
    examples: Tuple[DivergentTick, ...]
    ticks: int

    @property
    def first(self) -> DivergentTick:
        """The first tick the difference shows on."""
        return self.examples[0]

    def counted(
        self,
        divergent: DivergentTick,
        *,
        examples: int,
    ) -> Self:
        """The divergence once one more tick shows it, that tick joining the examples where it tells more.

        Args:
            divergent: The tick.
            examples: How many examples the divergence keeps at most.

        Returns:
            Self: The divergence, counting the tick.
        """
        last = self.examples[-1]
        telling = (
            len(self.examples) < examples
            and divergent.position != last.position
            and (divergent.application, divergent.engine) != (last.application, last.engine)
        )
        return replace(
            self,
            examples=self.examples + (divergent,) if telling else self.examples,
            ticks=self.ticks + 1,
        )


@dataclass(frozen=True)
class TimingDivergence:
    """The first tick the two players place at different rows.

    Attributes:
        tick: The tick.
        position: Where the application places it.
        engine_position: Where the tracker places it.
    """

    tick: int
    position: TickPosition
    engine_position: TickPosition


@dataclass(frozen=True)
class TraceComparison:
    """How one pass through a song sounds in a tracker against how it sounds in the application.

    Attributes:
        application_ticks: The ticks the application plays.
        engine_ticks: The ticks the tracker plays.
        timing: The first tick the two place at different rows, or ``None`` where every shared tick
            falls on the same row.
        divergences: Every way a channel sounds differently, in the order they first show.
    """

    application_ticks: int
    engine_ticks: int
    timing: Optional[TimingDivergence]
    divergences: Tuple[Divergence, ...]

    @property
    def matches(self) -> bool:
        """Whether the tracker plays every tick the application plays, and sounds each alike."""
        return self.application_ticks == self.engine_ticks and self.timing is None and not self.divergences


def differing_fields(
    application: ChannelSound,
    engine: ChannelSound,
) -> Tuple[SoundField, ...]:
    """What differs between two sounds of one channel on one tick.

    A channel silent on both sides sounds alike whatever its registers hold, and one that sounds on
    one side alone differs in that and nothing further. The volume covers whether the chip holds the
    level, so a channel its own envelope or counters move differs in volume from one it holds.

    Args:
        application: What the application sounds.
        engine: What the tracker sounds.

    Returns:
        Tuple[SoundField, ...]: The fields that differ, empty where the two sound alike.
    """
    if not application.audible and not engine.audible:
        return ()

    if application.audible != engine.audible:
        return (SoundField.AUDIBLE,)

    compared = (
        (SoundField.PERIOD, application.period, engine.period),
        (SoundField.VOLUME, (application.volume, application.held), (engine.volume, engine.held)),
        (SoundField.TIMBRE, application.timbre, engine.timbre),
    )
    return tuple(field for field, expected, played in compared if expected != played)


def first_timing_divergence(
    application: SongTrace,
    engine: SongTrace,
) -> Optional[TimingDivergence]:
    """The first tick both players reach and place at different rows.

    Args:
        application: What the application plays.
        engine: What the tracker plays.

    Returns:
        Optional[TimingDivergence]: That tick, or ``None`` where every shared tick falls alike.
    """
    for tick, (position, engine_position) in enumerate(zip(application.positions, engine.positions)):
        if position != engine_position:
            return TimingDivergence(
                tick=tick,
                position=position,
                engine_position=engine_position,
            )

    return None


def channel_divergences(
    channel: ChannelName,
    application: SongTrace,
    engine: SongTrace,
    *,
    examples: int,
) -> List[Divergence]:
    """Every way one channel sounds differently across the ticks both players reach.

    Args:
        channel: The channel compared.
        application: What the application plays.
        engine: What the tracker plays.
        examples: How many examples each divergence keeps at most.

    Returns:
        List[Divergence]: One entry per set of differing fields, in the order they first show.
    """
    found: Dict[Tuple[SoundField, ...], Divergence] = {}
    shared = min(application.ticks, engine.ticks)
    for tick in range(shared):
        expected = application.channels[channel][tick]
        played = engine.channels[channel][tick]
        fields = differing_fields(expected, played)
        if not fields:
            continue

        divergent = DivergentTick(
            tick=tick,
            position=application.positions[tick],
            application=expected,
            engine=played,
        )
        seen = found.get(fields)
        found[fields] = (
            Divergence(
                channel=channel,
                fields=fields,
                examples=(divergent,),
                ticks=1,
            )
            if seen is None
            else seen.counted(divergent, examples=examples)
        )

    return list(found.values())


def compare_traces(
    application: SongTrace,
    engine: SongTrace,
    *,
    examples: int,
) -> TraceComparison:
    """Holds what a tracker plays of a song against what the application plays of it, tick by tick.

    Tick 0 is the song's first tick on both sides, so a tick index names the same moment wherever the
    rows fall. Each tick of each channel is compared once both sides have been read into registers.

    Args:
        application: What the application plays.
        engine: What the tracker plays.
        examples: How many examples each divergence keeps at most.

    Returns:
        TraceComparison: The lengths, the first tick the rows part, and every divergence.
    """
    divergences = [
        divergence
        for channel in ChannelName.items()
        for divergence in channel_divergences(
            channel,
            application,
            engine,
            examples=examples,
        )
    ]
    return TraceComparison(
        application_ticks=application.ticks,
        engine_ticks=engine.ticks,
        timing=first_timing_divergence(application, engine),
        divergences=tuple(sorted(divergences, key=lambda divergence: divergence.first.tick)),
    )
