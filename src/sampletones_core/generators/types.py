from typing import Tuple, Type, TypeVar, Union

from sampletones_core.constants.enums import GeneratorClassName

from .implementation.noise import NoiseGenerator
from .implementation.pulse import PulseGenerator
from .implementation.triangle import TriangleGenerator

GeneratorT = TypeVar("GeneratorT", PulseGenerator, TriangleGenerator, NoiseGenerator)
GeneratorClass = Type[GeneratorT]
GeneratorUnion = Union[PulseGenerator, TriangleGenerator, NoiseGenerator]
GeneratorTypeUnion = Union[Type[PulseGenerator], Type[TriangleGenerator], Type[NoiseGenerator]]
GeneratorClassNames = Union[GeneratorClassName, Tuple[GeneratorClassName, ...]]
