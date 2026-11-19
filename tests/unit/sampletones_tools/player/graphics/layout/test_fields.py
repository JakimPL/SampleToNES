from dataclasses import dataclass
from typing import Dict, Final, Type, Union

import pytest
from pydantic import BaseModel, ValidationError

from sampletones_tools.player.graphics.layout.cells import LAST_COLUMN, LAST_ROW
from sampletones_tools.player.graphics.layout.fields import (
    ChannelFields,
    KeyboardFields,
    ProgramFields,
    ProgressField,
    TextField,
    TransportFields,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

Stated = Dict[str, Union[int, Dict[str, int]]]

ROW: Final[int] = 4
COLUMN: Final[int] = 6
WIDTH: Final[int] = 10
BELOW_THE_SCREEN: Final[int] = LAST_ROW + 1
RIGHT_OF_THE_SCREEN: Final[int] = LAST_COLUMN + 1

LINE: Final[Dict[str, int]] = {"row": ROW, "column": COLUMN, "width": WIDTH}
PROGRAM: Final[Stated] = {
    "title": LINE,
    "artist": {**LINE, "row": ROW + 1},
    "copyright": {**LINE, "row": ROW + 2},
}
TRANSPORT: Final[Stated] = {
    "row": ROW,
    "state_column": COLUMN,
    "played_column": COLUMN + 2,
    "total_column": COLUMN + 8,
}
PROGRESS: Final[Stated] = {"row": ROW, "column": COLUMN, "width": WIDTH}
CHANNELS: Final[Stated] = {
    "wave_column": COLUMN,
    "note_column": COLUMN + 6,
    "meter_column": COLUMN + 10,
    "pulse1_row": ROW,
    "pulse2_row": ROW + 2,
    "triangle_row": ROW + 4,
    "noise_row": ROW + 6,
}
KEYBOARD: Final[Stated] = {"lane_row": ROW, "key_row": ROW + 1, "column": COLUMN}


@dataclass(frozen=True, kw_only=True)
class FieldCase(BaseRegularTestCase):
    model: Type[BaseModel]
    stated: Stated


class TestFieldsOnTheScreen(BaseTestSuite):
    test_cases = (
        FieldCase(model=TextField, stated={**LINE}, label="a line of text"),
        FieldCase(model=ProgramFields, stated=PROGRAM, label="the program lines"),
        FieldCase(model=TransportFields, stated=TRANSPORT, label="the transport"),
        FieldCase(model=ProgressField, stated=PROGRESS, label="the progress bar"),
        FieldCase(model=ChannelFields, stated=CHANNELS, label="the channels"),
        FieldCase(model=KeyboardFields, stated=KEYBOARD, label="the keyboard"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_fields_are_held_as_stated(self, test_case: FieldCase) -> None:
        assert test_case.model.model_validate(test_case.stated).model_dump() == test_case.stated

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_field_the_model_does_not_name_is_refused(self, test_case: FieldCase) -> None:
        with pytest.raises(ValidationError, match="unnamed"):
            test_case.model.model_validate({**test_case.stated, "unnamed": ROW})


class TestAFieldOffTheScreen(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        model: Type[BaseModel]
        stated: Stated
        expected: str

    test_cases = (
        TestCase(
            model=TextField,
            stated={**LINE, "row": BELOW_THE_SCREEN},
            expected="row",
            label="a line below the screen",
        ),
        TestCase(
            model=TextField,
            stated={**LINE, "column": RIGHT_OF_THE_SCREEN},
            expected="column",
            label="a line right of the screen",
        ),
        TestCase(model=TextField, stated={**LINE, "width": 0}, expected="width", label="a line of no width"),
        TestCase(
            model=ProgramFields,
            stated={**PROGRAM, "copyright": {**LINE, "row": BELOW_THE_SCREEN}},
            expected="copyright.row",
            label="a program line below the screen",
        ),
        TestCase(
            model=ProgramFields,
            stated={**PROGRAM, "title": {**LINE, "width": 0}},
            expected="title.width",
            label="a program line of no width",
        ),
        TestCase(
            model=TransportFields,
            stated={**TRANSPORT, "row": BELOW_THE_SCREEN},
            expected="row",
            label="a transport below the screen",
        ),
        TestCase(
            model=TransportFields,
            stated={**TRANSPORT, "total_column": RIGHT_OF_THE_SCREEN},
            expected="total_column",
            label="a total time right of the screen",
        ),
        TestCase(
            model=ProgressField,
            stated={**PROGRESS, "width": 0},
            expected="width",
            label="a progress bar of no width",
        ),
        TestCase(
            model=ProgressField,
            stated={**PROGRESS, "row": -1},
            expected="row",
            label="a progress bar above the screen",
        ),
        TestCase(
            model=ChannelFields,
            stated={**CHANNELS, "noise_row": BELOW_THE_SCREEN},
            expected="noise_row",
            label="a channel below the screen",
        ),
        TestCase(
            model=ChannelFields,
            stated={**CHANNELS, "meter_column": RIGHT_OF_THE_SCREEN},
            expected="meter_column",
            label="a meter right of the screen",
        ),
        TestCase(
            model=KeyboardFields,
            stated={**KEYBOARD, "key_row": BELOW_THE_SCREEN},
            expected="key_row",
            label="keys below the screen",
        ),
        TestCase(
            model=KeyboardFields,
            stated={**KEYBOARD, "column": -1},
            expected="column",
            label="a keyboard left of the screen",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_the_field(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            test_case.model.model_validate(test_case.stated)
