from typing import Type, TypeAlias, TypeVar, Union

from generators.generator import Generator
from generators.noise import NoiseGenerator
from generators.pulse import PulseGenerator
from generators.triangle import TriangleGenerator

GeneratorType = TypeVar("GeneratorType", bound=Generator)
GeneratorClass: TypeAlias = Type[GeneratorType]
GeneratorUnion = Union[
    PulseGenerator,
    TriangleGenerator,
    NoiseGenerator,
]
