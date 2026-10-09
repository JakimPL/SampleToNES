from typing import List

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import (
    DUTY_CYCLES,
    MAX_VOLUME,
    MIN_PITCH,
    MIN_SOUNDING_PULSE_TIMER,
    MIXER_PULSE,
)
from sampletones_core.instructions import InstructionTypeUnion, PulseInstruction
from sampletones_core.timers import PhaseTimer
from sampletones_shared.types.data import Initials

from ..tonal import TonalGenerator


class PulseGenerator(TonalGenerator[PulseInstruction]):
    """The square channel, one of the chip's two pulses.

    A timer below ``MIN_SOUNDING_PULSE_TIMER`` renders silence while the timer runs on. The sweep unit
    mutes the channel there whatever the sweep's own setting, and the waveform keeps stepping.
    """

    def __init__(
        self,
        config: Config,
        name: str = ChannelName.PULSE1,
    ) -> None:
        super().__init__(config, name)
        self.timer = PhaseTimer(
            sample_rate=config.library.sample_rate,
            nes_frequency=config.library.nes_frequency,
            reset_phase=config.generation.reset_phase,
            phase_increment=1.0,
        )

    def __call__(
        self,
        pulse_instruction: PulseInstruction,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        if not isinstance(pulse_instruction, PulseInstruction):
            raise TypeError("instruction must be an instance of PulseInstruction")

        self.validate(initials)
        if not pulse_instruction.on:
            return np.zeros(self.frame_length, dtype=np.float32)

        output = self.generate(
            pulse_instruction,
            initials=initials,
            save=save,
        )

        self.save_state(save, pulse_instruction)

        if self.timer.timer < MIN_SOUNDING_PULSE_TIMER:
            return np.zeros(self.frame_length, dtype=np.float32)

        return output

    def apply(self, output: np.ndarray, instruction: PulseInstruction) -> np.ndarray:
        duty_cycle = DUTY_CYCLES[instruction.duty_cycle]
        output = np.where(output < duty_cycle, 1.0, -1.0).astype(np.float32)
        output *= np.float32(MIXER_PULSE * instruction.volume / MAX_VOLUME)
        return output

    def get_possible_instructions(self) -> List[PulseInstruction]:
        pulse_instructions = [
            PulseInstruction(
                on=False,
                pitch=MIN_PITCH,
                volume=0,
                duty_cycle=0,
            ),
        ]

        for pitch in self.frequency_table:
            for volume in range(1, MAX_VOLUME + 1):
                for duty_cycle in range(len(DUTY_CYCLES)):
                    pulse_instructions.append(
                        PulseInstruction(
                            on=True,
                            pitch=pitch,
                            volume=volume,
                            duty_cycle=duty_cycle,
                        )
                    )

        return pulse_instructions

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return PulseInstruction

    @classmethod
    def class_name(cls) -> GeneratorClassName:
        return GeneratorClassName.PULSE_GENERATOR
