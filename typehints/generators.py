from typing import Any, TypeVar

from generators.generator import Generator

GeneratorType = TypeVar("GeneratorType", bound="Generator[Any, Any]")
