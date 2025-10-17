from typing import Any, Literal, Optional, Tuple

Initials = Optional[Tuple[Any, ...]]

GeneratorClassNameValues = "PulseGenerator", "TriangleGenerator", "NoiseGenerator"
GeneratorClassName = Literal["PulseGenerator", "TriangleGenerator", "NoiseGenerator"]
