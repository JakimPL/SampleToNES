from sampletones_tools.web.colors import DARK_SCHEME, LIGHT_SCHEME, color_scheme, css_color


class TestCssColor:
    def test_an_opaque_color_is_six_digits(self) -> None:
        assert css_color((26, 27, 38, 255)) == "#1a1b26"

    def test_a_translucent_color_carries_its_alpha(self) -> None:
        assert css_color((26, 27, 38, 170)) == "#1a1b26aa"


class TestColorScheme:
    def test_a_dark_ground_asks_for_the_dark_scheme(self) -> None:
        assert color_scheme((28, 27, 38, 255)) == DARK_SCHEME

    def test_a_light_ground_asks_for_the_light_scheme(self) -> None:
        assert color_scheme((230, 232, 236, 255)) == LIGHT_SCHEME
