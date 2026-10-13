from pathlib import Path

import pytest

from sampletones_application.layout.fonts import Step, Typeface
from sampletones_tools.web.design import ApplicationDesign
from sampletones_tools.web.paths import FONTS_DIRECTORY
from sampletones_tools.web.typography.metrics import FontMetrics
from sampletones_tools.web.typography.scale import TYPEFACE_FILES, size_name, type_sizes


class TestTypeSizes:
    def test_every_typeface_and_step_has_a_size(self, design: ApplicationDesign) -> None:
        sizes = type_sizes(design.fonts, FONTS_DIRECTORY)

        assert set(sizes) == {size_name(typeface, step) for typeface in Typeface for step in Step}

    @pytest.mark.parametrize("typeface", list(Typeface))
    def test_a_size_is_the_application_size_in_the_face_s_ems(
        self,
        design: ApplicationDesign,
        typeface: Typeface,
    ) -> None:
        factor = FontMetrics.read(FONTS_DIRECTORY / TYPEFACE_FILES[typeface]).em_per_pixel_height
        expected = design.fonts.size_for(typeface, Step.MEDIUM) * design.fonts.scale * factor

        assert type_sizes(design.fonts, FONTS_DIRECTORY)[size_name(typeface, Step.MEDIUM)] == pytest.approx(
            expected, abs=0.01
        )

    def test_a_missing_face_is_reported(self, design: ApplicationDesign, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            type_sizes(design.fonts, tmp_path)
