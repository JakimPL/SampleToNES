from typing import Final

import pytest

from sampletones_shared.meta.import_boundary.configs.general import GeneralBoundaries

GENERAL: Final[GeneralBoundaries] = GeneralBoundaries(
    groups={
        "visual": ("dearpygui", "package.ui"),
        "contracts": ("package.services.result",),
    },
)


class TestGroupPrefixes:
    """A group gathers the prefixes several rules reach for, so the set is written once."""

    def test_a_group_is_spelled_out_as_the_prefixes_it_gathers(self) -> None:
        assert GENERAL.prefixes(("visual",)) == ("dearpygui", "package.ui")

    def test_several_groups_follow_the_order_they_are_named_in(self) -> None:
        assert GENERAL.prefixes(("contracts", "visual")) == (
            "package.services.result",
            "dearpygui",
            "package.ui",
        )

    def test_naming_no_group_reaches_no_prefix(self) -> None:
        assert GENERAL.prefixes(()) == ()

    def test_a_name_reaching_no_group_is_reported(self) -> None:
        with pytest.raises(KeyError):
            GENERAL.prefixes(("absent",))
