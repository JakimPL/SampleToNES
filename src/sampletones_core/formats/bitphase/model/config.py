from typing import Final

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

BITPHASE_MODEL_CONFIG: Final[ConfigDict] = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
)
