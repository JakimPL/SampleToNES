from typing import Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_shared.meta.import_boundary.configs.general import GeneralBoundaries
from sampletones_shared.meta.import_boundary.rule import BoundaryRule


class BoundaryDeclaration(BaseModel):
    """One boundary as it is written, naming the groups it draws on.

    A rule reaching for a set several others share names the group instead of repeating it, so
    the set stays one statement. What is written here becomes the rule the check runs once the
    groups are spelled out.

    Attributes:
        root: Directory under the source root the pattern is written against.
        pattern: Glob naming the modules the declaration reaches.
        forbidden_groups: Groups whose prefixes are out of reach in them.
        forbidden: Import prefixes out of reach in them, beyond the groups'.
        contract_groups: Groups whose prefixes are exempt from the forbidden ones.
        contracts: Import prefixes exempt from the forbidden ones, beyond the groups'.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str
    pattern: str
    forbidden_groups: Tuple[str, ...] = ()
    forbidden: Tuple[str, ...] = ()
    contract_groups: Tuple[str, ...] = ()
    contracts: Tuple[str, ...] = ()

    def rule(self, general: GeneralBoundaries) -> BoundaryRule:
        """The rule the declaration amounts to, with every group it names spelled out.

        A group's prefixes lead the ones written beside them, so the rule reads in the order it
        was declared: the shared set first, the declaration's own prefixes after.

        Args:
            general: The names the declaration is written in.

        Returns:
            BoundaryRule: The boundary the check runs.

        Raises:
            KeyError: If the declaration names a group the vocabulary leaves out.
        """
        return BoundaryRule(
            root=self.root,
            pattern=self.pattern,
            forbidden=(
                *general.prefixes(self.forbidden_groups),
                *self.forbidden,
            ),
            contracts=(
                *general.prefixes(self.contract_groups),
                *self.contracts,
            ),
        )
