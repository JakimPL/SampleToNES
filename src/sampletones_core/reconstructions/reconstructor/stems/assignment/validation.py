from typing import Dict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig


def validate_stems_config(
    stems_config: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
) -> None:
    """Holds a stems setup against the channels the run was built for.

    The setup states its own consistency — unique ids, a hierarchy naming every entry, a cap of
    at least one — so what is left to check is the pairing with this run: every channel a stem
    may occupy has a generator to render it.

    Raises:
        ValueError: If a stem allows a channel the run has no generator for.
    """
    enabled = set(channels)
    for entry in stems_config.entries:
        foreign = entry.channel_set - enabled
        if foreign:
            raise ValueError(f"Stem {entry.id} allows channels the run was not built for: {sorted(foreign)}")
