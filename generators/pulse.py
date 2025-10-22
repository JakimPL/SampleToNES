from typing import List, cast

import numpy as np

from configs.config import Config
from constants import DUTY_CYCLES, MAX_VOLUME, MIN_PITCH, MIXER_PULSE
from generators.generator import Generator
from instructions.pulse import PulseInstruction
from timers.phase import PhaseTimer
from typehints.general import GeneratorClassName, Initials


class PulseGenerator(Generator[PulseInstruction, PhaseTimer]):
    def __init__(self, config: Config, name: str = "pulse") -> None:
        super().__init__(config, name)
        self.timer = PhaseTimer(
            sample_rate=config.general.sample_rate,
            change_rate=config.general.change_rate,
            reset_phase=config.generation.reset_phase,
            phase_increment=1.0,
        )

    def __call__(
        self,
        pulse_instruction: PulseInstruction,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)

        if not pulse_instruction.on:
            return np.zeros(self.frame_length, dtype=np.float32)

        output = self.generate(pulse_instruction, initials=initials)
        self.save_state(save, pulse_instruction, initials)

        return output

    def set_timer(self, pulse_instruction: PulseInstruction) -> None:
        if pulse_instruction.on:
            self.timer.frequency = self.get_frequency(pulse_instruction.pitch)
        else:
            self.timer.frequency = 0.0

    def apply(self, output: np.ndarray, pulse_instruction: PulseInstruction) -> np.ndarray:
        duty_cycle = DUTY_CYCLES[pulse_instruction.duty_cycle]
        output = np.where(output < duty_cycle, 1.0, -1.0)
        output *= pulse_instruction.volume / MAX_VOLUME
        return output * MIXER_PULSE

    def get_possible_instructions(self) -> List[PulseInstruction]:
        pulse_instructions = [PulseInstruction(on=False, pitch=MIN_PITCH, volume=0, duty_cycle=0)]

        for pitch in self.frequency_table:
            for volume in range(1, MAX_VOLUME + 1):
                for duty_cycle in range(len(DUTY_CYCLES)):
                    pulse_instructions.append(
                        PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)
                    )

        return pulse_instructions

    @staticmethod
    def get_instruction_type() -> type:
        return PulseInstruction

    @classmethod
    def class_name(cls) -> GeneratorClassName:
        return cast(GeneratorClassName, cls.__name__)
