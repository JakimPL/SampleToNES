from typing import Dict, List, NamedTuple, Tuple

from sampletones_shared.meta.import_boundary.rule import BoundaryRule
from sampletones_shared.meta.import_boundary.units import nested_globs, unit_glob, unit_prefix


class LayerGraph(NamedTuple):
    """A tree of modules, the units it divides into, and what each unit may import.

    Attributes:
        root: Directory under the source root the units are named within.
        package: Import prefix the units sit under, empty where the units are packages themselves.
        layers: Each unit and the units it may import.
    """

    root: str
    package: str
    layers: Dict[str, Tuple[str, ...]]

    def rules(self) -> List[BoundaryRule]:
        """One rule per unit, forbidding every unit its layers leave out.

        Declaring what a unit may import states the graph once, and the rule the check runs is what
        remains — so an edge the graph leaves out is reported wherever it is taken. A unit declared
        inside another owns its own modules, which is how a subpackage states a boundary of its own
        inside the one around it.

        Returns:
            List[BoundaryRule]: The rules the graph amounts to, in declaration order.
        """
        return [
            BoundaryRule(
                root=self.root,
                pattern=unit_glob(unit),
                forbidden=tuple(
                    unit_prefix(self.package, other) for other in self.layers if other != unit and other not in allowed
                ),
                excluding=nested_globs(unit, self.layers),
            )
            for unit, allowed in self.layers.items()
        ]
