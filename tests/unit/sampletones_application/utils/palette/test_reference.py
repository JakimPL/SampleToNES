import pytest

from sampletones_application.utils.palette.reference import PaletteReference, is_reference


class TestPaletteReference:
    def test_a_bare_token_carries_no_alpha_override(self) -> None:
        reference = PaletteReference.model_validate(".accent")
        assert reference.token == "accent"
        assert reference.alpha is None

    def test_a_token_with_alpha_captures_the_fraction(self) -> None:
        reference = PaletteReference.model_validate(".accent/0.5")
        assert reference.token == "accent"
        assert reference.alpha == 0.5

    def test_a_value_without_the_prefix_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            PaletteReference.model_validate("#a97fe3")

    def test_an_alpha_outside_the_unit_range_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            PaletteReference.model_validate(".accent/1.5")


class TestIsReference:
    @pytest.mark.parametrize("value", [".accent", ".accent/0.5", "  .accent"])
    def test_a_prefixed_value_reads_as_a_reference(self, value: str) -> None:
        assert is_reference(value)

    @pytest.mark.parametrize("value", ["#a97fe3", "accent", ""])
    def test_any_other_value_reads_as_a_literal(self, value: str) -> None:
        assert not is_reference(value)
