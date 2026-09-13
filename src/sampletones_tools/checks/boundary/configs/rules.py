from typing import Dict, Self, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_shared.utils.serialization import load_yaml_model_dir
from sampletones_tools.checks.boundary.configs.declaration import BoundaryDeclaration
from sampletones_tools.checks.boundary.configs.general import GeneralBoundaries
from sampletones_tools.checks.boundary.configs.paths import BOUNDARIES_DIRECTORY
from sampletones_tools.checks.boundary.graph import LayerGraph
from sampletones_tools.checks.boundary.rule import BoundaryRule
from sampletones_tools.checks.boundary.standalone import StandaloneRule
from sampletones_tools.checks.boundary.token import TokenRule


class ImportBoundaryRules(BaseModel):
    """Every boundary the source tree is held to, as the shipped configuration states it.

    The declaration comes in four forms, each a fragment of its own. A layer graph names a tree
    of modules and what each unit may import, and amounts to one rule per unit. A boundary
    declaration names one directory and the imports it stays clear of. A token rule names a
    spelling a tree keeps out. A standalone rule names the scripts that run on the system
    interpreter and holds them to the standard library. The general vocabulary holds the prefix
    sets the declarations draw on, so a set several of them reach for is written once.

    Attributes:
        general: The names the declarations are written in.
        graphs: Each layer graph the source tree divides into, under the name the documents give it.
        rules: The boundaries written directly.
        tokens: The spellings kept out of the trees they name.
        standalone: The scripts held to the standard library and the tree they sit in.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    general: GeneralBoundaries
    graphs: Dict[str, LayerGraph]
    rules: Tuple[BoundaryDeclaration, ...]
    tokens: Tuple[TokenRule, ...]
    standalone: Tuple[StandaloneRule, ...]

    @model_validator(mode="after")
    def _validate_every_named_group_is_declared(self) -> Self:
        """Holds each declaration to the vocabulary, so a name reaching no group is refused as it is read.

        Raises:
            ValueError: If a declaration names a group the general configuration leaves out.
        """
        named = {
            name for declaration in self.rules for name in (*declaration.forbidden_groups, *declaration.contract_groups)
        }
        unknown = sorted(named - set(self.general.groups))
        if unknown:
            raise ValueError(f"the declarations name groups the vocabulary leaves out: {', '.join(unknown)}")

        return self

    @classmethod
    def load(cls) -> Self:
        """The boundaries the build ships.

        Returns:
            Self: The declaration validated from `sampletones_config/boundaries/`.

        Raises:
            TypeError: If a fragment holds anything other than what its field states.
        """
        return load_yaml_model_dir(BOUNDARIES_DIRECTORY, cls)

    def boundary_rules(self) -> Tuple[BoundaryRule, ...]:
        """Every import boundary the check runs, the graphs' rules first and the declared ones after.

        Returns:
            Tuple[BoundaryRule, ...]: The rules the declaration amounts to, in declaration order.
        """
        return (
            *(rule for graph in self.graphs.values() for rule in graph.rules()),
            *(declaration.rule(self.general) for declaration in self.rules),
        )
