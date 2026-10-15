from typing import Final

from sampletones_tools.checks.boundary.configs.declaration import BoundaryDeclaration
from sampletones_tools.checks.boundary.configs.general import GeneralBoundaries

ROOT: Final[str] = "package"
PATTERN: Final[str] = "logic/**/*.py"
CONFINED: Final[str] = "logic/library/adapter.py"

GENERAL: Final[GeneralBoundaries] = GeneralBoundaries(
    groups={
        "visual": ("dearpygui", "package.ui"),
        "contracts": ("package.services.result",),
    },
)


class TestDeclaredRule:
    """What a declaration is written as, and the rule it amounts to."""

    def test_a_declaration_naming_no_group_states_its_own_prefixes(self) -> None:
        declaration = BoundaryDeclaration(
            root=ROOT,
            pattern=PATTERN,
            forbidden=("package.services",),
        )

        assert declaration.rule(GENERAL).forbidden == ("package.services",)

    def test_a_named_group_leads_the_prefixes_written_beside_it(self) -> None:
        declaration = BoundaryDeclaration(
            root=ROOT,
            pattern=PATTERN,
            forbidden_groups=("visual",),
            forbidden=("package.services",),
        )

        assert declaration.rule(GENERAL).forbidden == (
            "dearpygui",
            "package.ui",
            "package.services",
        )

    def test_a_group_reaches_the_contracts_the_same_way(self) -> None:
        declaration = BoundaryDeclaration(
            root=ROOT,
            pattern=PATTERN,
            forbidden=("package.services",),
            contract_groups=("contracts",),
        )

        assert declaration.rule(GENERAL).contracts == ("package.services.result",)

    def test_the_rule_is_written_against_the_tree_the_declaration_names(self) -> None:
        declaration = BoundaryDeclaration(
            root=ROOT,
            pattern=PATTERN,
            forbidden=("package.services",),
        )
        rule = declaration.rule(GENERAL)

        assert (rule.root, rule.pattern) == (ROOT, PATTERN)

    def test_a_declaration_leaves_the_modules_it_excludes_to_their_own_rules(self) -> None:
        declaration = BoundaryDeclaration(
            root=ROOT,
            pattern=PATTERN,
            forbidden=("library",),
            excluding=(CONFINED,),
        )

        assert declaration.rule(GENERAL).excluding == (CONFINED,)

    def test_a_declaration_excluding_nothing_reaches_every_module_of_its_pattern(self) -> None:
        declaration = BoundaryDeclaration(
            root=ROOT,
            pattern=PATTERN,
            forbidden=("library",),
        )

        assert declaration.rule(GENERAL).excluding == ()
