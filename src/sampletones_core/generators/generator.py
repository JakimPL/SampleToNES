from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import MIN_SAMPLE_LENGTH
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import CyclicArray
from sampletones_core.instructions import InstructionT, InstructionTypeUnion
from sampletones_core.timers import TimerT, get_frequency_table
from sampletones_shared.types.data import Initials


class Generator(ABC, Generic[InstructionT, TimerT]):
    """
    Synthesizes one NES channel's audio from the instructions that drive it.

    A generator owns a timer that produces the channel's raw oscillator waveform and
    shapes that waveform into the channel's timbre and level. Each concrete generator
    (pulse, triangle, noise) targets one channel: it declares the instruction type it
    accepts, enumerates every instruction it can emit, and renders either a frame or a
    single looping sample for that channel.

    Calling the generator with an instruction renders one frame of audio, and
    `save_state` carries oscillator continuity from one frame into the next, so a held
    note stays phase-continuous across frames until `reset` clears that history.
    """

    def __init__(self, config: Config, name: str) -> None:
        """Builds a generator bound to a configuration and channel name.

        Args:
            config: Configuration supplying the sample rate, frame length, and the
                pitch-to-frequency table.
            name: The channel this generator drives (e.g. ``"pulse1"``).

        Raises:
            TypeError: If ``config`` is not a ``Config`` or ``name`` is not a ``str``.
        """
        if not isinstance(config, Config):
            raise TypeError("config must be an instance of Config")

        if not isinstance(name, str):
            raise TypeError(f"name must be an instance of str, got {type(name)}")

        self.config: Config = config
        self.frequency_table: Dict[int, float] = get_frequency_table(config)

        self.name: str = name
        self.clock: Optional[float] = None
        self.previous_instruction: Optional[InstructionT] = None

        self.timer: TimerT

    @abstractmethod
    def __call__(
        self,
        instruction: InstructionT,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        """Renders one frame of audio for the given instruction.

        Args:
            instruction: The command describing this frame's pitch, volume, and timbre.
            initials: Oscillator state to resume from, or ``None`` to start fresh.
            save: When true, record this frame's ending state so the next call continues
                from it.

        Returns:
            np.ndarray: One frame of float32 samples; a silent instruction yields a zero
                frame.
        """

    def generate(
        self,
        instruction: InstructionT,
        initials: Initials = None,
        save: bool = True,
    ) -> np.ndarray:
        """Runs the timer for the instruction and shapes its waveform.

        Sets the timer for the instruction, runs it to produce the raw oscillator
        waveform, then applies the instruction's timbre and level.

        Args:
            instruction: The command describing this frame's pitch, volume, and timbre.
            initials: Oscillator state to resume from, or ``None`` to start fresh.
            save: When true, keep the timer's ending state for the next call.

        Returns:
            np.ndarray: The shaped frame of float32 samples.
        """
        self.set_timer(instruction)
        output = self.timer(initials=initials, save=save)
        output = self.apply(output, instruction)
        return output

    def generate_sample(self, instruction: InstructionT) -> CyclicArray:
        """Renders one looping-period sample for the library.

        A silent instruction yields a short zero sample; an audible one yields a single
        oscillator period shaped by the instruction, ready to loop.

        Args:
            instruction: The command describing the sample's pitch, volume, and timbre.

        Returns:
            CyclicArray: The looping sample at the configured sample rate.
        """
        if not instruction.on:
            min_sample_length = round(MIN_SAMPLE_LENGTH * self.config.library.sample_rate)
            return CyclicArray(
                array=np.zeros(min_sample_length, dtype=np.float32),
                sample_rate=self.config.library.sample_rate,
            )

        self.set_timer(instruction)
        output = self.timer.generate_sample()
        output.array = self.apply(output.array, instruction)
        return output

    def save_state(self, save: bool, instruction: InstructionT) -> None:
        """Remembers the instruction as the previous one when ``save`` is set.

        Recording the previous instruction lets the next frame continue the oscillator
        from where this one ended.

        Args:
            save: Whether to keep this instruction as the continuation point.
            instruction: The instruction just rendered.
        """
        if save:
            self.previous_instruction = instruction

    @abstractmethod
    def set_timer(self, instruction: InstructionT) -> None:
        """Configures the timer to sound the given instruction.

        Args:
            instruction: The command whose pitch sets the timer's frequency; a silent
                instruction sets it to zero.
        """

    @abstractmethod
    def apply(self, output: np.ndarray, instruction: InstructionT) -> np.ndarray:
        """Shapes the timer's raw waveform into the channel's timbre and level.

        Args:
            output: The raw oscillator waveform from the timer.
            instruction: The command whose timbre and volume shape the waveform.

        Returns:
            np.ndarray: The shaped float32 waveform.
        """

    def reset(self) -> None:
        """Clears frame-to-frame history so the next call starts fresh.

        Drops the previous instruction and resets the timer, so the next render begins
        without carried-over oscillator state.
        """
        self.previous_instruction = None
        self.timer.reset()

    def validate(self, initials: Initials) -> None:
        """Checks that the given oscillator state is usable as a resume point.

        Args:
            initials: The oscillator state a render would resume from.
        """
        self.timer.validate(initials)

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.timer.initials

    def get_frequency(self, pitch: int) -> float:
        """The oscillator frequency in Hz for a MIDI pitch.

        Args:
            pitch: The MIDI pitch to look up.

        Returns:
            float: The frequency in Hz from the generator's frequency table.

        Raises:
            KeyError: If the pitch is absent from the frequency table.
        """
        return self.frequency_table[pitch]

    @abstractmethod
    def get_possible_instructions(self) -> List[InstructionT]:
        """Every instruction this generator can emit.

        The reconstruction library is built by rendering a sample for each instruction
        returned here.

        Returns:
            List[InstructionT]: The generator's full instruction vocabulary.
        """

    @property
    def frame_length(self) -> int:
        return self.config.library.frame_length

    @classmethod
    @abstractmethod
    def class_name(cls) -> GeneratorClassName:
        """The enum tag identifying this concrete generator type.

        Returns:
            GeneratorClassName: The tag used to serialize and dispatch generators by type.
        """

    @classmethod
    @abstractmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        """The instruction type this generator accepts.

        Returns:
            InstructionTypeUnion: The concrete instruction type paired with this generator.
        """
