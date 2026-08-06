from dataclasses import dataclass
from typing import Mapping, Optional, Tuple


@dataclass(frozen=True)
class TypeEnvironment:
    """The types stated for the expressions a scope names.

    A spelling is a name or an attribute chain as the source writes it, so both `language_manager`
    and `self._language_manager` name the object a lookup reads from.
    """

    types: Mapping[str, str]

    def type_of(self, spelling: str) -> Optional[str]:
        """The type name stated for one spelling.

        Args:
            spelling: Name or attribute chain, such as `element` or `self._language_manager`.

        Returns:
            Optional[str]: The type name, or `None` where the scope states none.
        """
        return self.types.get(spelling)

    def spellings_of(self, type_name: str) -> Tuple[str, ...]:
        """Every spelling stated to hold the named type.

        Args:
            type_name: Simple type name, as an annotation writes it.

        Returns:
            Tuple[str, ...]: The spellings, ordered as they were read.
        """
        return tuple(spelling for spelling, name in self.types.items() if name == type_name)
