from typing import Any, Literal, Optional, Tuple

Initials = Optional[Tuple[Any, ...]]

GeneratorClassNameValues = "SquareGenerator", "TriangleGenerator", "NoiseGenerator"
GeneratorClassName = Literal["SquareGenerator", "TriangleGenerator", "NoiseGenerator"]
