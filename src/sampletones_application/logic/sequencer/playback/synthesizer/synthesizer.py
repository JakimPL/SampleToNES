from dataclasses import replace
from typing import Callable, FrozenSet, List, Optional, Tuple

import numpy as np

from sampletones_application.logic.shared.project_source import ProjectSource
from sampletones_core.audio import clip_audio_inplace, silence
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project import Project
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition
from sampletones_core.timing import Groove

from .bank import ChannelBank
from .frames import RowFrames
from .modifiers import apply_modifiers
from .rates import EngineRates
from .state import ChannelState
from .timing import SongTiming
from .voice import SampleVoice


class RowSynthesizer:
    """Synthesis engine for tracker song audio, one row at a time.

    Reads the ``Project`` from ``project_source`` on every ``render_row`` call. Over the live
    controller that makes pattern edits, tempo changes, and sample swaps take effect immediately
    while playback keeps running; over a
    :class:`~sampletones_application.logic.shared.project_source.ProjectSnapshot` it makes a whole
    render describe one state of the document.

    A row lasts the ticks the project's groove gives its position within the pattern, so the
    row a pattern's tenth row plays for is the row an exported module plays it for: both index
    the same groove from the pattern's first row.

    Each of those ticks spans the samples the :class:`~sampletones_core.timing.clock.TickClock`
    gives its position in the run, so a tick lasts ``1 / nes_frequency`` seconds at every sample
    rate and the groove's tempo is the tempo heard.

    ``sample_rate`` reports the rate the audio is rendered at, and is what the caller taking that
    audio runs at: the output device for live playback, the chosen format for a file. Reading it
    per row keeps the two in step, so a rendered second is a second wherever the audio goes.

    Generators are held in a :class:`ChannelBank` built from ``config`` at the rates the first row
    is rendered at, so the rate is asked for once there is audio to take it — a device is chosen by
    the time playback starts, and a format by the time a render does. They carry timer state across
    rows for phase continuity within a sustained note, and triggering a new note calls
    ``generator.reset()`` for a clean phase start.

    ``active_channels`` reports which channels sound and is consulted once per channel per
    row, so muting or unmuting during playback is heard as the render-ahead buffer drains. A
    silenced channel still takes each row's instrument, transpose, and volume, so unmuting
    resumes on the state the pattern has reached.
    """

    def __init__(
        self,
        project_source: ProjectSource,
        config: Config,
        *,
        active_channels: Callable[[], FrozenSet[GeneratorName]],
        sample_rate: Callable[[], int],
    ) -> None:
        self._project_source = project_source
        self._config = config
        self._active_channels = active_channels
        self._sample_rate = sample_rate
        self._position = SongPosition()
        self._timing: SongTiming = SongTiming.from_project(project_source.project)
        self._groove: Groove = self._timing.groove()
        self._channels: Optional[ChannelBank] = None
        self._elapsed_ticks: int = 0

    @property
    def order_position(self) -> int:
        return self._position.order_position

    @property
    def row_index(self) -> int:
        return self._position.row_index

    @property
    def is_finished(self) -> bool:
        project = self._project_source.project
        return self._position.order_position >= project.song.order_length()

    def set_position(self, order_position: int, row_index: int) -> None:
        self._position.order_position = order_position
        self._position.row_index = row_index

    def reset(self) -> None:
        self._elapsed_ticks = 0
        if self._channels is not None:
            self._channels.reset()

    def render_row(self) -> Tuple[np.ndarray, SongPosition]:
        project = self._project_source.project
        song = project.song
        self._position.wrap_overflow(song.rows_per_pattern)
        channels = self._bank()
        self._ensure_groove(project)

        frames = RowFrames.from_clock(
            channels.clock,
            elapsed_ticks=self._elapsed_ticks,
            ticks=self._groove.ticks[self._position.row_index],
        )

        position_before = replace(self._position)
        finished = self.is_finished
        mixed = (
            silence(frames.total)
            if finished
            else self._mix_channels(
                project,
                song,
                frames,
                channels,
            )
        )

        self._elapsed_ticks += len(frames.lengths)
        if not finished:
            self._advance_position(song)

        return mixed, position_before

    def _bank(self) -> ChannelBank:
        """The channels the row about to be rendered sounds through, at the rates in force.

        Building them here is what lets a session start where nothing yet takes the audio: the rate
        belongs to whoever consumes it, so it is asked for at the moment there is a consumer to
        answer. Every later row follows the pair, so a device or a format changing underneath is
        heard from the next row on.
        """
        rates = self._current_rates()
        if self._channels is None:
            self._channels = ChannelBank(self._config, rates)
        else:
            self._channels.follow(rates)

        return self._channels

    def _current_rates(self) -> EngineRates:
        return EngineRates.from_project(
            self._project_source.project,
            self._sample_rate(),
        )

    def _ensure_groove(self, project: Project) -> None:
        """Rebuilds the groove when the row rate or the metre it is spread over changes.

        An engine that holds a row for a whole number of ticks reaches a fractional row rate by
        varying that number from row to row, and the groove is where those counts are decided.
        Rebuilding only on a timing edit keeps a tempo change immediate while the distribution
        itself, which spans a whole pattern, is computed once.
        """
        timing = SongTiming.from_project(project)
        if timing == self._timing:
            return

        self._timing = timing
        self._groove = timing.groove()

    def _mix_channels(
        self,
        project: Project,
        song: Song,
        frames: RowFrames,
        channels: ChannelBank,
    ) -> np.ndarray:
        mixed = silence(frames.total)
        for generator_name in GeneratorName.items():
            channel_audio = self._render_channel(
                generator_name,
                project,
                song,
                frames,
                channels,
            )
            mixed += channel_audio

        return clip_audio_inplace(mixed)

    def _render_channel(
        self,
        generator_name: GeneratorName,
        project: Project,
        song: Song,
        frames: RowFrames,
        channels: ChannelBank,
    ) -> np.ndarray:
        state = channels.state(generator_name)

        row = self._resolve_row(generator_name, song)
        if row is not None:
            self._apply_row_to_state(state, row)

        sample_id = state.sample_id
        if sample_id is None or generator_name not in self._active_channels():
            return silence(frames.total)

        return self._synthesize_ticks(
            state,
            sample_id,
            project,
            generator_name,
            frames,
        )

    def _resolve_row(
        self,
        generator_name: GeneratorName,
        song: Song,
    ) -> Optional[Row]:
        if self._position.order_position >= song.order_length():
            return None

        order_entry = song.order[self._position.order_position].get(generator_name)
        if order_entry is None:
            return None

        pattern = song.pattern(generator_name, order_entry)
        if pattern is None or self._position.row_index >= len(pattern.rows):
            return None

        return pattern.rows[self._position.row_index]

    def _apply_row_to_state(self, state: ChannelState, row: Row) -> None:
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
        state: ChannelState,
        sample_id: str,
        project: Project,
        generator_name: GeneratorName,
        frames: RowFrames,
    ) -> np.ndarray:
        sample = project.sample(sample_id)
        if sample is None:
            return silence(frames.total)

        instructions = sample.reconstruction.instructions[generator_name]
        if not instructions:
            return silence(frames.total)

        voice = SampleVoice.read(sample.reconstruction, generator_name)
        output = silence(frames.total)
        silence_frame = silence(frames.longest)

        for tick, frame_length in enumerate(frames.lengths):
            frame = self._synthesize_tick(
                state,
                instructions,
                silence_frame[:frame_length],
                sample.loop,
                frame_length,
                voice,
            )
            output[frames.bounds[tick] : frames.bounds[tick + 1]] = frame
            state.tick_index += 1

        return output

    def _synthesize_tick(
        self,
        state: ChannelState,
        instructions: List[InstructionUnion],
        silence_frame: np.ndarray,
        loop: bool,
        frame_length: int,
        voice: SampleVoice,
    ) -> np.ndarray:
        if loop:
            instruction = instructions[state.tick_index % len(instructions)]
        elif state.tick_index < len(instructions):
            instruction = instructions[state.tick_index]
        else:
            return silence_frame

        state.generator.frame_length = frame_length
        return state.generator(
            apply_modifiers(
                voice.sound(instruction, state.feature_values),
                state.transpose,
                state.volume,
            ),
            save=True,
        )

    def _advance_position(self, song: Song) -> None:
        self._position.advance(song.rows_per_pattern, song.order_length())
