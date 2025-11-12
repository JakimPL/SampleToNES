from typing import Type, TypeAlias, TypeVar, Union

from .generator import Generator
from .noise import NoiseGenerator
from .pulse import PulseGenerator
from .triangle import TriangleGenerator

GeneratorType = TypeVar("GeneratorType", bound=Generator)
GeneratorClass: TypeAlias = Type[GeneratorType]
GeneratorUnion = Union[
    PulseGenerator,
    TriangleGenerator,
    NoiseGenerator,
]
