from types import SimpleNamespace
from typing import Dict, Final

from sampletones_application.utils.file_dialogs.backends.portal.response import (
    CURRENT_FILTER_RESULT,
    SUCCESS_CODE,
    URIS_RESULT,
    ChooserResult,
)
from sampletones_application.utils.file_dialogs.backends.portal.variant import Variant

URI: Final[str] = "file:///home/user/kick.json"
OTHER_URI: Final[str] = "file:///home/user/snare.json"
LABEL: Final[str] = "Bitphase instrument preset (*.json)"
DISMISSED_CODE: Final[int] = 1

URIS_SIGNATURE: Final[str] = "as"
FILTER_SIGNATURE: Final[str] = "(sa(us))"


def _response(
    code: int,
    results: Dict[str, Variant],
) -> SimpleNamespace:
    return SimpleNamespace(body=(code, results))


class TestChooserResult:
    def test_the_chosen_locations_arrive_in_the_dialog_s_order(self) -> None:
        response = _response(SUCCESS_CODE, {URIS_RESULT: (URIS_SIGNATURE, [URI, OTHER_URI])})

        assert ChooserResult.from_response(response) == ChooserResult(
            uris=(URI, OTHER_URI),
            filter_label=None,
        )

    def test_the_reported_filter_names_the_type_the_selector_stood_on(self) -> None:
        """The portal reports the whole filter, and its label is what names the type."""
        response = _response(
            SUCCESS_CODE,
            {
                URIS_RESULT: (URIS_SIGNATURE, [URI]),
                CURRENT_FILTER_RESULT: (FILTER_SIGNATURE, (LABEL, [(0, "*.json")])),
            },
        )

        assert ChooserResult.from_response(response) == ChooserResult(uris=(URI,), filter_label=LABEL)

    def test_a_dismissal_answers_with_nothing(self) -> None:
        assert ChooserResult.from_response(_response(DISMISSED_CODE, {})) is None

    def test_a_response_carrying_no_locations_answers_with_none_chosen(self) -> None:
        response = _response(SUCCESS_CODE, {CURRENT_FILTER_RESULT: (FILTER_SIGNATURE, (LABEL, []))})

        assert ChooserResult.from_response(response) == ChooserResult(uris=(), filter_label=LABEL)
