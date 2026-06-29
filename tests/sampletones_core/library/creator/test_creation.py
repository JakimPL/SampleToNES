import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_map
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.library import InstructionLibraryFragment
from sampletones_core.library.creator.creation import (
    generate_instruction,
    generate_single_instruction_task,
)


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


@pytest.fixture(scope="module")
def window(config: Config) -> Window:
    return Window.from_config(config)


@pytest.fixture(scope="module")
def pulse_instruction() -> PulseInstruction:
    return PulseInstruction.default_instruction()


class TestGenerateInstruction:
    def test_generates_fragment_for_pulse_instruction(
        self,
        config: Config,
        window: Window,
        pulse_instruction: PulseInstruction,
    ) -> None:
        generators = get_generators_map(config)
        extractor = get_feature_extractor(config, window)
        _, fragment = generate_instruction(
            generators,
            GeneratorClassName.PULSE_GENERATOR,
            pulse_instruction,
            extractor,
        )
        assert isinstance(fragment, InstructionLibraryFragment)

    def test_returned_instruction_matches_input(
        self,
        config: Config,
        window: Window,
        pulse_instruction: PulseInstruction,
    ) -> None:
        generators = get_generators_map(config)
        extractor = get_feature_extractor(config, window)
        returned_instruction, _ = generate_instruction(
            generators,
            GeneratorClassName.PULSE_GENERATOR,
            pulse_instruction,
            extractor,
        )
        assert returned_instruction is pulse_instruction


class TestGenerateSingleInstructionTask:
    def test_single_task_returns_instruction_and_fragment(
        self,
        config: Config,
        window: Window,
        pulse_instruction: PulseInstruction,
    ) -> None:
        task = (
            (GeneratorClassName.PULSE_GENERATOR, pulse_instruction),
            config,
            window,
        )
        _, fragment = generate_single_instruction_task(task)
        assert isinstance(fragment, InstructionLibraryFragment)

    def test_single_task_instruction_matches_input(
        self,
        config: Config,
        window: Window,
        pulse_instruction: PulseInstruction,
    ) -> None:
        task = (
            (GeneratorClassName.PULSE_GENERATOR, pulse_instruction),
            config,
            window,
        )
        instruction, _ = generate_single_instruction_task(task)
        assert instruction is pulse_instruction
