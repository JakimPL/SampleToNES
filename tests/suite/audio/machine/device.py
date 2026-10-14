from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class FakeDevice:
    """One device of the fake machine: its name, the rates it plays at, and how many channels it plays."""

    name: str
    default_sample_rate: int
    supported_sample_rates: Tuple[int, ...]
    output_channels: int
    host_api: int
