from typing import Optional

from sampletones_application.utils.theme.spec import BASE_THEME_NAME, ThemeSpec


def _spec(name: str, *, extends: Optional[str]) -> ThemeSpec:
    return ThemeSpec(name=name, tag=f"tag.{name}", extends=extends, components=[])


class TestParent:
    def test_a_theme_inherits_the_base_by_default(self) -> None:
        assert _spec("converter", extends=None).parent == BASE_THEME_NAME

    def test_the_base_theme_stands_alone(self) -> None:
        assert _spec(BASE_THEME_NAME, extends=None).parent is None

    def test_an_explicit_parent_is_respected(self) -> None:
        assert _spec("child", extends="table").parent == "table"
