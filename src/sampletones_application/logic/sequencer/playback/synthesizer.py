from dataclasses import dataclass, field, replace
from typing import FrozenSet, List, Optional

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_PITCH, MAX_VOLUME, MIN_PITCH
from sampletones_core.generators.maps import GENERATOR_CLASSES, MIXER_LEVELS
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.project import Project
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.constants.project import REFERENCE_NES_FREQUENCY, REFERENCE_TEMPO

from .protocol import ChannelGeneratorProtocol


@dataclass
class _ChannelState:
    generator: ChannelGeneratorProtocol
    sample_id: Optional[str] = field(default=None)
    tick_index: int = field(default=0)
    transpose: int = field(default=0)
    volume: int = field(default=MAX_VOLUME)


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
    immediately without restarting playback.

    Generators are constructed once from ``config`` and carry timer state across
    rows for phase continuity within a sustained note. Triggering a new note
    calls ``generator.reset()`` for a clean phase start.
    """

    def __init__(self, project_controller: ProjectController, config: Config) -> None:
        self._project_controller = project_controller
        self._config = config
        self._nes_frequency: int = config.library.nes_frequency
        self._position = SongPosition()
        self._tick_debt: int = 0
        self._active_channels: FrozenSet[GeneratorName] = frozenset(GeneratorName.items())
        self._channel_states: dict[GeneratorName, _ChannelState] = {
            generator_name: _ChannelState(
                generator=GENERATOR_CLASSES[generator_name](
                    config,
                    generator_name.value,
                ),
            )
            for generator_name in GeneratorName.items()
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

    def set_channel_mask(self, active_channels: FrozenSet[GeneratorName]) -> None:
        self._active_channels = active_channels

    def reset(self) -> None:
        self._tick_debt = 0
        for state in self._channel_states.values():
            state.sample_id = None
            state.tick_index = 0
            state.transpose = 0
            state.volume = MAX_VOLUME

    def _ensure_generators(self, nes_frequency: int) -> None:
        """Rebuilds the channel generators when the engine refresh rate changes.

        ``nes_frequency`` is the rate at which instructions (engine ticks) are
        consumed, so each tick spans ``sample_rate / nes_frequency`` audio samples.
        The generators must follow the project's current value so a row keeps a
        constant real-time duration as the rate changes (the tempo is otherwise tied
        to the frequency). Pitch is derived from the APU clock, not this rate, so only
        the per-tick frame length changes; the generators' phase continuity resets,
        which is acceptable for an occasional settings edit.
        """
        if nes_frequency == self._nes_frequency:
            return

        self._nes_frequency = nes_frequency
        config = self._playback_config(nes_frequency)
        for generator_name, state in self._channel_states.items():
            state.generator = GENERATOR_CLASSES[generator_name](config, generator_name.value)

    def _playback_config(self, nes_frequency: int) -> Config:
        library = self._config.library.model_copy(update={"nes_frequency": nes_frequency})
        return self._config.model_copy(update={"library": library})

    def render_row(self) -> tuple[np.ndarray, SongPosition]:
        project = self._project_controller.project
        settings = project.settings
        song = project.song
        self._position.wrap_overflow(song.rows_per_pattern)
        self._ensure_generators(settings.nes_frequency)

        frame_length = round(self._config.library.sample_rate / settings.nes_frequency)
        ticks_per_row = self._ticks_for_row(settings)
        chunk_length = frame_length * ticks_per_row

        position_before = replace(self._position)
        if self.is_finished:
            return np.zeros(chunk_length, dtype=np.float32), position_before

        mixed = self._mix_channels(
            project,
            song,
            frame_length,
            ticks_per_row,
            chunk_length,
        )
        self._advance_position(song)

        return mixed, position_before

    def _ticks_for_row(self, settings: ProjectSettings) -> int:
        """ticks_per_row == speed at REFERENCE_TEMPO and REFERENCE_NES_FREQUENCY."""
        self._tick_debt += settings.speed * settings.nes_frequency * REFERENCE_TEMPO
        return self._drain_tick_debt(settings.tempo)

    def _drain_tick_debt(self, tempo: int) -> int:
        divisor = tempo * REFERENCE_NES_FREQUENCY
        ticks = self._tick_debt // divisor
        self._tick_debt -= ticks * divisor
        return ticks

    def _mix_channels(
        self,
        project: Project,
        song: Song,
        frame_length: int,
        ticks_per_row: int,
        chunk_length: int,
    ) -> np.ndarray:
        mixed = _silence(chunk_length)
        for generator_name in GeneratorName.items():
            channel_audio = self._render_channel(
                generator_name,
                project,
                song,
                frame_length,
                ticks_per_row,
                chunk_length,
            )
            mixer_level = MIXER_LEVELS[self._channel_states[generator_name].generator.class_name()]
            mixed += channel_audio * mixer_level

        np.clip(mixed, -1.0, 1.0, out=mixed)
        return mixed

    def _render_channel(
        self,
        generator_name: GeneratorName,
        project: Project,
        song: Song,
        frame_length: int,
        ticks_per_row: int,
        chunk_length: int,
    ) -> np.ndarray:
        state = self._channel_states[generator_name]

        row = self._resolve_row(generator_name, song)
        if row is None:
            return _silence(chunk_length)

        self._apply_row_to_state(state, row)

        sample_id = state.sample_id
        if sample_id is None or generator_name not in self._active_channels:
            return _silence(chunk_length)

        return self._synthesize_ticks(
            state,
            sample_id,
            project,
            generator_name,
            frame_length,
            ticks_per_row,
            chunk_length,
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
        if row.instrument is not None:
            state.generator.reset()
            state.sample_id = row.instrument.sample_id
            state.tick_index = 0
            state.transpose = row.transpose if row.transpose is not None else 0
            state.volume = row.volume if row.volume is not None else MAX_VOLUME
        elif row.transpose is not None or row.volume is not None:
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
        frame_length: int,
        ticks_per_row: int,
        chunk_length: int,
    ) -> np.ndarray:
        sample = project.sample(sample_id)
        if sample is None:
            return _silence(chunk_length)

        instructions = sample.reconstruction.instructions.get(generator_name)
        if not instructions:
            return _silence(chunk_length)

        output = _silence(chunk_length)
        silence_frame = _silence(frame_length)

        for tick in range(ticks_per_row):
            frame = self._synthesize_tick(
                state,
                instructions,
                silence_frame,
                sample.loop,
            )
            output[tick * frame_length : (tick + 1) * frame_length] = frame
            state.tick_index += 1

        return output

    def _synthesize_tick(
        self,
        state: _ChannelState,
        instructions: List[InstructionUnion],
        silence_frame: np.ndarray,
        loop: bool,
    ) -> np.ndarray:
        if loop:
            instruction = instructions[state.tick_index % len(instructions)]
        elif state.tick_index < len(instructions):
            instruction = instructions[state.tick_index]
        else:
            return silence_frame

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
