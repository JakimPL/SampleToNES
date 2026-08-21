from typing import Dict, Final, List, Mapping, Self, Set, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_shared.meta.import_boundary.rule import BoundaryRule
from sampletones_shared.meta.import_boundary.units import (
    nested_globs,
    unit_glob,
    unit_prefix,
)

SOURCE_TREE: Final[str] = ""


def reached_units(layers: Mapping[str, Tuple[str, ...]], unit: str) -> Set[str]:
    """Every unit one unit imports, directly or through the units it imports.

    Args:
        layers: Each unit and the units it may import.
        unit: Unit to walk out from.

    Returns:
        Set[str]: The units it reaches, itself among them where the graph closes a cycle.

    Raises:
        KeyError: If a unit is reached that the layers leave undeclared.
    """
    reached: Set[str] = set()
    pending = [unit]
    while pending:
        for allowed in layers[pending.pop()]:
            if allowed not in reached:
                reached.add(allowed)
                pending.append(allowed)

    return reached


class LayerGraph(BaseModel):
    """A tree of modules, the units it divides into, and what each unit may import.

    Attributes:
        root: Directory under the source root the units are named within, empty where the units
            sit at the source root itself.
        package: Import prefix the units sit under, empty where the units are packages themselves.
        layers: Each unit and the units it may import.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str = SOURCE_TREE
    package: str = SOURCE_TREE
    layers: Dict[str, Tuple[str, ...]]

    @model_validator(mode="after")
    def _validate_every_layer_a_unit_may_import_is_declared(self) -> Self:
        """Holds each unit's layers to the units the graph divides into.

        Raises:
            ValueError: If a unit may import something the graph leaves undeclared.
        """
        undeclared = sorted(
            {allowed for layers in self.layers.values() for allowed in layers} - set(self.layers),
        )
        if undeclared:
            raise ValueError(f"the graph leaves the units it reaches undeclared: {', '.join(undeclared)}")

        return self

    @model_validator(mode="after")
    def _validate_the_graph_is_acyclic(self) -> Self:
        """Holds the units to an order, which is what makes a unit's layers state a level.

        Raises:
            ValueError: If a unit reaches itself through the units it may import.
        """
        looping = sorted(unit for unit in self.layers if unit in reached_units(self.layers, unit))
        if looping:
            raise ValueError(f"the units reach themselves through the graph: {', '.join(looping)}")

        return self

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
                    unit_prefix(
                        self.package,
                        other,
                    )
                    for other in self.layers
                    if other != unit and other not in allowed
                ),
                excluding=nested_globs(unit, self.layers),
            )
            for unit, allowed in self.layers.items()
        ]
