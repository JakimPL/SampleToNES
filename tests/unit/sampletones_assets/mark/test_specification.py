from dataclasses import dataclass
from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_assets.mark.specification import Mark
from tests.suite.case import BaseRegularTestCase

VALID_FRAME: Final[Dict[str, Any]] = {
    "grid": 64,
    "corner_radius": 14,
    "rim": {"inset": 1, "width": 2, "opacity": 0.14},
}

VALID_COLORS: Final[Dict[str, Any]] = {
    "background": {"top": "#3a3650", "bottom": "#211d30"},
    "sine": "#64c8ff",
    "square": "#ffc864",
    "rim": "#cdb6ff",
}

VALID_SINE: Final[Dict[str, Any]] = {
    "start": {"x": 8, "y": 32},
    "curves": [
        {
            "control_start": {"x": 11, "y": 16},
            "control_end": {"x": 15, "y": 16},
            "end": {"x": 18, "y": 32},
        },
    ],
}

VALID_SQUARE: Final[Dict[str, Any]] = {
    "points": [
        {"x": 18, "y": 32},
        {"x": 18, "y": 20},
        {"x": 28, "y": 20},
    ],
}

VALID_WAVES: Final[Dict[str, Any]] = {
    "width": 4,
    "sine": VALID_SINE,
    "square": VALID_SQUARE,
}

VALID_RENDER: Final[Dict[str, Any]] = {
    "supersample": 16,
    "curve_samples": 96,
    "raster_size": 256,
    "windows_sizes": [256, 128, 64],
}

VALID_FIELDS: Final[Dict[str, Any]] = {
    "frame": VALID_FRAME,
    "colors": VALID_COLORS,
    "waves": VALID_WAVES,
    "render": VALID_RENDER,
}


class TestMark:
    @dataclass(frozen=True, kw_only=True)
    class InvalidFieldCase(BaseRegularTestCase):
        field: str
        value: Any

    test_cases = (
        InvalidFieldCase(
            field="frame",
            value={**VALID_FRAME, "grid": 0},
            label="empty_grid",
        ),
        InvalidFieldCase(
            field="frame",
            value={**VALID_FRAME, "corner_radius": 33},
            label="corner_radius_over_half_the_grid",
        ),
        InvalidFieldCase(
            field="frame",
            value={**VALID_FRAME, "rim": {**VALID_FRAME["rim"], "inset": 14}},
            label="rim_inset_outside_the_corner_radius",
        ),
        InvalidFieldCase(
            field="frame",
            value={**VALID_FRAME, "rim": {**VALID_FRAME["rim"], "opacity": 1.5}},
            label="rim_opacity_over_full",
        ),
        InvalidFieldCase(
            field="colors",
            value={**VALID_COLORS, "sine": "64c8ff"},
            label="color_without_a_hash",
        ),
        InvalidFieldCase(
            field="colors",
            value={**VALID_COLORS, "sine": "#64c8"},
            label="color_of_four_hex_digits",
        ),
        InvalidFieldCase(
            field="waves",
            value={**VALID_WAVES, "width": 0},
            label="wave_without_width",
        ),
        InvalidFieldCase(
            field="waves",
            value={**VALID_WAVES, "sine": {**VALID_SINE, "curves": []}},
            label="smooth_half_without_curves",
        ),
        InvalidFieldCase(
            field="waves",
            value={**VALID_WAVES, "square": {"points": [{"x": 18, "y": 32}]}},
            label="stepped_half_without_a_segment",
        ),
        InvalidFieldCase(
            field="waves",
            value={
                **VALID_WAVES,
                "square": {"points": [{"x": 18, "y": 32}, {"x": 28, "y": 20}]},
            },
            label="stepped_segment_turning_on_both_axes",
        ),
        InvalidFieldCase(
            field="waves",
            value={
                **VALID_WAVES,
                "square": {"points": [{"x": 40, "y": 32}, {"x": 40, "y": 20}]},
            },
            label="halves_meeting_apart",
        ),
        InvalidFieldCase(
            field="render",
            value={**VALID_RENDER, "supersample": 0},
            label="drawing_below_the_design_grid",
        ),
        InvalidFieldCase(
            field="render",
            value={**VALID_RENDER, "windows_sizes": []},
            label="windows_icon_without_a_frame",
        ),
        InvalidFieldCase(
            field="render",
            value={**VALID_RENDER, "windows_sizes": [64, 128, 256]},
            label="windows_sizes_in_ascending_order",
        ),
        InvalidFieldCase(
            field="render",
            value={**VALID_RENDER, "windows_sizes": [256, 256, 128]},
            label="repeated_windows_size",
        ),
    )

    def test_the_packaged_definition_loads(self) -> None:
        mark = Mark.load()
        assert isinstance(mark, Mark)

    def test_the_sample_of_the_packaged_definition_leaves_as_it_entered(self) -> None:
        """The mark draws one wave, so the stepped half carries on from where the smooth half arrives."""
        mark = Mark.load()
        assert mark.waves.square.points[0] == mark.waves.sine.end

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_an_invalid_field_is_rejected(self, case: InvalidFieldCase) -> None:
        fields = {**VALID_FIELDS, case.field: case.value}
        with pytest.raises(ValidationError):
            Mark.model_validate(fields)

    @pytest.mark.parametrize("field", sorted(VALID_FIELDS))
    def test_a_missing_field_is_rejected(self, field: str) -> None:
        fields = {key: value for key, value in VALID_FIELDS.items() if key != field}
        with pytest.raises(ValidationError):
            Mark.model_validate(fields)

    def test_an_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Mark.model_validate({**VALID_FIELDS, "shadow": {"blur": 4}})
