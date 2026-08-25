from typing import Dict, Sequence, Tuple

from pydantic import BaseModel, ConfigDict


class GeneralBoundaries(BaseModel):
    """The names the boundary declarations are written in.

    A group gathers the import prefixes several rules reach for as one thing — the interface a
    layer stays clear of, the data contracts it may read — so the set is stated once and each
    rule names it.

    Attributes:
        groups: Each named set of import prefixes and the prefixes it gathers.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    groups: Dict[str, Tuple[str, ...]]

    def prefixes(self, names: Sequence[str]) -> Tuple[str, ...]:
        """The import prefixes the named groups gather, in the order they are named.

        Args:
            names: Groups to spell out.

        Returns:
            Tuple[str, ...]: Every prefix those groups hold.

        Raises:
            KeyError: If a name reaches no declared group.
        """
        return tuple(prefix for name in names for prefix in self.groups[name])
