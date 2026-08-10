from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import accumulate
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple

import numpy as np

from sampletones_application.constants.playback import (
    MAX_TICKS_PER_ROW,
    MIN_TICKS_PER_ROW,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.audio import clip_audio_inplace
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_PITCH, MAX_VOLUME, MIN_PITCH
from sampletones_core.generators.maps import GENERATOR_CLASSES
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.project import Project
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition
from sampletones_core.timing import Groove, Metre, RowRate, TickClock, calculate_groove

from .protocol import ChannelGeneratorProtocol


@dataclass
class _ChannelState:
    generator: ChannelGeneratorProtocol
    sample_id: Optional[str] = field(default=None)
    tick_index: int = field(default=0)
    transpose: int = field(default=0)
    volume: int = field(default=MAX_VOLUME)


@dataclass(frozen=True)
class _SongTiming:
    """Everything a project's groove is built from, held together so a change is one comparison.

    Attributes:
        rate: The exact ticks one row lasts under the project's tempo, speed and tick rate.
        metre: The pattern length and the beat and bar grouping the ticks are spread over.
    """

    rate: RowRate
    metre: Metre

    @classmethod
    def from_project(cls, project: Project) -> _SongTiming:
        """Reads the timing a project plays at, taking the pattern length from its song."""
        return cls(
            rate=RowRate.from_settings(project.settings),
            metre=Metre.from_settings(
                project.settings,
                rows=project.song.rows_per_pattern,
            ),
        )

    def groove(self) -> Groove:
        """Spreads the row rate across a pattern's rows.

        Playback follows whatever tempo the project states, so the one bound it sets is that
        every row lasts at least a tick and keeps sounding; the ceiling is the fastest row the
        settings can ask for, which leaves the groove free to realize the rate exactly.
        """
        return calculate_groove(
            self.rate,
            self.metre,
            minimum_ticks=MIN_TICKS_PER_ROW,
            maximum_ticks=MAX_TICKS_PER_ROW,
        )


@dataclass(frozen=True)
class _EngineRates:
    """The pair of rates a tick is sized from, held together so a change is one comparison.

    Each rate is owned elsewhere: the project states how many instructions the engine consumes
    each second, and whoever takes the audio states the rate it is rendered at — the output
    device for playback, the chosen format for a file. Together they fix how many samples one
    tick spans, so the synthesiser follows both.

    Attributes:
        nes_frequency: The engine ticks consumed each second.
        sample_rate: The samples the rendered audio holds each second.
    """

    nes_frequency: int
    sample_rate: int

    def clock(self) -> TickClock:
        """The samples each tick spans under this pair of rates."""
        return TickClock.from_parameters(
            sample_rate=self.sample_rate,
            nes_frequency=self.nes_frequency,
        )


@dataclass(frozen=True)
class _RowFrames:
    """Where each of a row's ticks starts and ends within the row's audio.

    A tick clock gives consecutive ticks whole sample counts that sum to their exact span, so the
    lengths within one row vary where the sample rate does not divide the tick rate. Resolving the
    boundaries once per row is what lets every channel write into the same offsets.

    Attributes:
        lengths: The samples each of the row's ticks spans, in order.
        bounds: Each tick's start offset, ending with the row's total length.
    """

    lengths: Tuple[int, ...]
    bounds: Tuple[int, ...]

    @classmethod
    def from_clock(
        cls,
        clock: TickClock,
        *,
        elapsed_ticks: int,
        ticks: int,
    ) -> _RowFrames:
        """Resolves the row starting at ``elapsed_ticks`` and spanning ``ticks`` ticks."""
        lengths = tuple(clock.frame_length(elapsed_ticks + tick) for tick in range(ticks))
        return cls(
            lengths=lengths,
            bounds=tuple(accumulate(lengths, initial=0)),
        )

    @property
    def total(self) -> int:
        """The samples the whole row spans."""
        return self.bounds[-1]

    @property
    def longest(self) -> int:
        """The samples the row's longest tick spans."""
        return max(self.lengths, default=0)


def _silence(samples: int) -> np.ndarray:
    return np.zeros(samples, dtype=np.float32)


def _apply_modifiers(
    instruction: InstructionUnion,
    transpose: int,
    row_volume: int,
) -> InstructionUnion:
    match instruction:
        case PulseInstruction():
            scaled_volume = max(0, min(MAX_VOLUME, round(instruction.volume * row_volume / MAX_VOLUME)))
            effective_pitch = max(MIN_PITCH, min(MAX_PITCH, instruction.pitch + transpose))
            return instruction.model_copy(update={"pitch": effective_pitch, "volume": scaled_volume})
        case TriangleInstruction():
            effective_pitch = max(MIN_PITCH, min(MAX_PITCH, instruction.pitch + transpose))
            on = instruction.on and row_volume > MAX_VOLUME // 2
            return instruction.model_copy(update={"pitch": effective_pitch, "on": on})
        case NoiseInstruction():
            scaled_volume = max(0, min(MAX_VOLUME, round(instruction.volume * row_volume / MAX_VOLUME)))
            effective_period = (instruction.period + transpose) % 16
            return instruction.model_copy(update={"period": effective_period, "volume": scaled_volume})


class RowSynthesizer:
    """Real-time synthesis engine for tracker song playback.

    Reads the live ``Project`` from ``project_controller`` on every ``render_row``
    call so that pattern edits, tempo changes, and sample swaps take effect
    immediately while playback keeps running.

    A row lasts the ticks the project's groove gives its position within the pattern, so the
    row a pattern's tenth row plays for is the row an exported module plays it for: both index
    the same groove from the pattern's first row.

    Each of those ticks spans the samples the :class:`~sampletones_core.timing.clock.TickClock`
    gives its position in the run, so a tick lasts ``1 / nes_frequency`` seconds at every sample
    rate and the groove's tempo is the tempo heard.

    ``sample_rate`` reports the rate the audio is rendered at, and is what the caller taking that
    audio runs at: the output device for live playback, the chosen format for a file. Reading it
    per row keeps the two in step, so a rendered second is a second wherever the audio goes.

    Generators are constructed from ``config`` at the rates in force and carry timer
    state across rows for phase continuity within a sustained note. Triggering a new
    note calls ``generator.reset()`` for a clean phase start.

    ``active_channels`` reports which channels sound and is consulted once per channel per
    row, so muting or unmuting during playback is heard as the render-ahead buffer drains. A
    silenced channel still takes each row's instrument, transpose, and volume, so unmuting
    resumes on the state the pattern has reached.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        config: Config,
        *,
        active_channels: Callable[[], FrozenSet[GeneratorName]],
        sample_rate: Callable[[], int],
    ) -> None:
        self._project_controller = project_controller
        self._config = config
        self._active_channels = active_channels
        self._sample_rate = sample_rate
        self._position = SongPosition()
        self._timing: _SongTiming = _SongTiming.from_project(project_controller.project)
        self._groove: Groove = self._timing.groove()
        self._rates: _EngineRates = self._current_rates()
        self._tick_clock: TickClock = self._rates.clock()
        self._elapsed_ticks: int = 0
        self._channel_states: Dict[GeneratorName, _ChannelState] = {
            generator_name: _ChannelState(generator=generator)
            for generator_name, generator in self._build_generators(self._rates).items()
        }

    @property
    def order_position(self) -> int:
        return self._position.order_position

    @property
    def row_index(self) -> int:
        return self._position.row_index

    @property
    def is_finished(self) -> bool:
        project = self._project_controller.project
        return self._position.order_position >= project.song.order_length()

    def set_position(self, order_position: int, row_index: int) -> None:
        self._position.order_position = order_position
        self._position.row_index = row_index

    def reset(self) -> None:
        self._elapsed_ticks = 0
        for state in self._channel_states.values():
            state.sample_id = None
            state.tick_index = 0
            state.transpose = 0
            state.volume = MAX_VOLUME

    def _ensure_generators(self) -> None:
        """Rebuilds the channel generators when either rate a tick is sized from changes.

        The engine consumes ``nes_frequency`` instructions a second and the audio holds
        ``sample_rate`` samples a second, so a tick spans the quotient of the two. Following the
        project's frequency keeps a row a constant real-time duration as that frequency changes,
        and following the output's rate keeps a rendered second a second wherever the audio goes.
        Pitch derives from the APU clock rather than either rate, so a change moves only the
        per-tick frame length; the generators' phase continuity resets, which is acceptable for an
        occasional settings edit.

        The tick clock follows the same pair, since it states how long one of those ticks lasts.
        """
        rates = self._current_rates()
        if rates == self._rates:
            return

        self._rates = rates
        self._tick_clock = rates.clock()
        for generator_name, generator in self._build_generators(rates).items():
            self._channel_states[generator_name].generator = generator

    def _current_rates(self) -> _EngineRates:
        return _EngineRates(
            nes_frequency=self._project_controller.project.settings.nes_frequency,
            sample_rate=self._sample_rate(),
        )

    def _build_generators(self, rates: _EngineRates) -> Dict[GeneratorName, ChannelGeneratorProtocol]:
        config = self._engine_config(rates)
        return {
            generator_name: GENERATOR_CLASSES[generator_name](
                config,
                generator_name.value,
            )
            for generator_name in GeneratorName.items()
        }

    def _engine_config(self, rates: _EngineRates) -> Config:
        return self._config.with_library(
            nes_frequency=rates.nes_frequency,
            sample_rate=rates.sample_rate,
        )

    def render_row(self) -> Tuple[np.ndarray, SongPosition]:
        project = self._project_controller.project
        song = project.song
        self._position.wrap_overflow(song.rows_per_pattern)
        self._ensure_generators()
        self._ensure_groove(project)

        frames = _RowFrames.from_clock(
            self._tick_clock,
            elapsed_ticks=self._elapsed_ticks,
            ticks=self._groove.ticks[self._position.row_index],
        )

        position_before = replace(self._position)
        finished = self.is_finished
        mixed = (
            _silence(frames.total)
            if finished
            else self._mix_channels(
                project,
                song,
                frames,
            )
        )

        self._elapsed_ticks += len(frames.lengths)
        if not finished:
            self._advance_position(song)

        return mixed, position_before

    def _ensure_groove(self, project: Project) -> None:
        """Rebuilds the groove when the row rate or the metre it is spread over changes.

        An engine that holds a row for a whole number of ticks reaches a fractional row rate by
        varying that number from row to row, and the groove is where those counts are decided.
        Rebuilding only on a timing edit keeps a tempo change immediate while the distribution
        itself, which spans a whole pattern, is computed once.
        """
        timing = _SongTiming.from_project(project)
        if timing == self._timing:
            return

        self._timing = timing
        self._groove = timing.groove()

    def _mix_channels(
        self,
        project: Project,
        song: Song,
        frames: _RowFrames,
    ) -> np.ndarray:
        mixed = _silence(frames.total)
        for generator_name in GeneratorName.items():
            channel_audio = self._render_channel(
                generator_name,
                project,
                song,
                frames,
            )
            mixed += channel_audio

        return clip_audio_inplace(mixed)

    def _render_channel(
        self,
        generator_name: GeneratorName,
        project: Project,
        song: Song,
        frames: _RowFrames,
    ) -> np.ndarray:
        state = self._channel_states[generator_name]

        row = self._resolve_row(generator_name, song)
        if row is not None:
            self._apply_row_to_state(state, row)

        sample_id = state.sample_id
        if sample_id is None or generator_name not in self._active_channels():
            return _silence(frames.total)

        return self._synthesize_ticks(
            state,
            sample_id,
            project,
            generator_name,
            frames,
        )

    def _resolve_row(self, generator_name: GeneratorName, song: Song) -> Optional[Row]:
        if self._position.order_position >= song.order_length():
            return None

        order_entry = song.order[self._position.order_position].get(generator_name)
        if order_entry is None:
            return None

        pattern = song.pattern(generator_name, order_entry)
        if pattern is None or self._position.row_index >= len(pattern.rows):
            return None

        return pattern.rows[self._position.row_index]

    def _apply_row_to_state(self, state: _ChannelState, row: Row) -> None:
        match row.command:
            case Instrument() as instrument:
                state.generator.reset()
                state.sample_id = instrument.sample_id
                state.tick_index = 0
                state.transpose = row.transpose if row.transpose is not None else 0
                state.volume = row.volume if row.volume is not None else MAX_VOLUME
            case NoteOff():
                state.generator.reset()
                state.sample_id = None
                state.tick_index = 0
            case None:
                if row.transpose is not None:
                    state.transpose = row.transpose
                if row.volume is not None:
                    state.volume = row.volume

    def _synthesize_ticks(
        self,
        state: _ChannelState,
        sample_id: str,
        project: Project,
        generator_name: GeneratorName,
        frames: _RowFrames,
    ) -> np.ndarray:
        sample = project.sample(sample_id)
        if sample is None:
            return _silence(frames.total)

        instructions = sample.reconstruction.instructions.get(generator_name)
        if not instructions:
            return _silence(frames.total)

        output = _silence(frames.total)
        silence_frame = _silence(frames.longest)

        for tick, frame_length in enumerate(frames.lengths):
            frame = self._synthesize_tick(
                state,
                instructions,
                silence_frame[:frame_length],
                sample.loop,
                frame_length,
            )
            output[frames.bounds[tick] : frames.bounds[tick + 1]] = frame
            state.tick_index += 1

        return output

    def _synthesize_tick(
        self,
        state: _ChannelState,
        instructions: List[InstructionUnion],
        silence_frame: np.ndarray,
        loop: bool,
        frame_length: int,
    ) -> np.ndarray:
        if loop:
            instruction = instructions[state.tick_index % len(instructions)]
        elif state.tick_index < len(instructions):
            instruction = instructions[state.tick_index]
        else:
            return silence_frame

        state.generator.frame_length = frame_length
        return state.generator(
            _apply_modifiers(
                instruction,
                state.transpose,
                state.volume,
            ),
            save=True,
        )

    def _advance_position(self, song: Song) -> None:
        self._position.advance(song.rows_per_pattern, song.order_length())
