from typing import Final

from sampletones_application.layout.fonts import FontScale, FontsLayout, Step, Typeface

SANS: Final[FontScale] = FontScale(small=11, medium=12, large=13, title=14)
MONO: Final[FontScale] = FontScale(small=21, medium=22, large=23, title=24)
ICON: Final[FontScale] = FontScale(small=31, medium=32, large=33, title=34)


class TestTheSizeLadder:
    """Every rung a font asks for answers with a size, on the typeface asking for it."""

    def test_every_rung_answers_with_the_size_the_scale_states(self) -> None:
        assert [SANS.step(step) for step in Step] == [11, 12, 13, 14]

    def test_a_typeface_answers_from_a_ladder_of_its_own(self) -> None:
        layout = FontsLayout(scale=1, sans=SANS, mono=MONO, icon=ICON)

        assert layout.size_for(Typeface.MONO, Step.TITLE) == 24
        assert layout.size_for(Typeface.SANS, Step.TITLE) == 14
