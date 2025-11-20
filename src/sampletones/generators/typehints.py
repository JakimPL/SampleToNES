from typing import Tuple, Type, TypeAlias, TypeVar, Union

from sampletones.constants.enums import GeneratorClassName

from .generator import Generator
from .noise import NoiseGenerator
from .pulse import PulseGenerator
from .triangle import TriangleGenerator

GeneratorT = TypeVar("GeneratorT", bound=Generator)
GeneratorClass: TypeAlias = Type[GeneratorT]
GeneratorUnion = Union[
    PulseGenerator,
    TriangleGenerator,
    NoiseGenerator,
]

GeneratorClassNames = Union[GeneratorClassName, Tuple[GeneratorClassName, ...]]
