from typing import Tuple, Type, TypeVar, Union

from sampletones.constants.enums import GeneratorClassName

from .noise import NoiseGenerator
from .pulse import PulseGenerator
from .triangle import TriangleGenerator

GeneratorT = TypeVar("GeneratorT", PulseGenerator, TriangleGenerator, NoiseGenerator)
GeneratorClass = Type[GeneratorT]
GeneratorUnion = Union[PulseGenerator, TriangleGenerator, NoiseGenerator]
GeneratorTypeUnion = Union[Type[PulseGenerator], Type[TriangleGenerator], Type[NoiseGenerator]]
GeneratorClassNames = Union[GeneratorClassName, Tuple[GeneratorClassName, ...]]
