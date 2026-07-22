from abc import ABC, abstractmethod
from typing import Self

from pydantic import ConfigDict

from sampletones_core.constants.enums import InstructionClassName
from sampletones_core.data import DataModel


class Instruction(DataModel, ABC):
    """
    A single-frame command that drives one generator channel.

    Each concrete instruction (pulse, triangle, noise) carries the parameters its
    generator reads to synthesize one frame of audio — pitch, volume, and any timbre
    controls — together with the ``on`` flag that decides whether the channel sounds.
    Instances are immutable and validated, so an instruction is a stable value safe to
    store, hash, and compare.

    Subclasses declare the parameter fields and implement the comparison, ordering, and
    canonical-instance methods below.

    Attributes:
        on: True when the channel sounds this frame.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    on: bool

    @property
    @abstractmethod
    def name(self) -> str:
        """A short human-readable label for the instruction, such as ``"P C-4 vF D50"``.

        Returns:
            str: The label used to display this instruction in the interface.
        """

    @abstractmethod
    def distance(self, other: Self) -> float:
        """A dissimilarity score between this instruction and another of the same type.

        The score is symmetric and lies in ``[0, 1]``: it reaches ``0`` for two
        instructions that sound identical and grows as their parameters diverge. Two
        silent instructions score ``0``.

        Args:
            other: Another instruction of the same concrete type.

        Returns:
            float: The dissimilarity in ``[0, 1]``.

        Raises:
            TypeError: If ``other`` is a different instruction type.
        """

    @abstractmethod
    def __lt__(self, other: Self) -> bool:
        """Orders instructions of the same type for sorting.

        Defines a total order over one concrete type, so a list of its instructions
        sorts into a stable, canonical sequence.

        Args:
            other: Another instruction of the same concrete type.

        Returns:
            bool: True when this instruction sorts before ``other``.

        Raises:
            TypeError: If ``other`` is a different instruction type.
        """

    @classmethod
    @abstractmethod
    def null_instruction(cls) -> Self:
        """Builds the silent instruction for this type.

        Returns:
            Self: An instruction with ``on`` false, standing for a frame in which the
                channel produces no sound.
        """

    @classmethod
    @abstractmethod
    def default_instruction(cls) -> Self:
        """Builds a baseline audible instruction for this type.

        Returns:
            Self: An instruction with ``on`` true and the type's baseline parameter
                values, serving as the starting point when a fresh instruction is needed.
        """

    @classmethod
    @abstractmethod
    def class_name(cls) -> InstructionClassName:
        """The enum tag identifying this concrete instruction type.

        Returns:
            InstructionClassName: The tag used to serialize and dispatch instructions
                by type.
        """
