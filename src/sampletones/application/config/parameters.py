from typing import Literal


class ConfigParameter:
    tag: str
    section: Literal["general", "library", "generation"]
