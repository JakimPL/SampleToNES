from dataclasses import dataclass
from typing import Dict, Final, List, Optional, Self, Tuple, cast

from jeepney.low_level import Message

from sampletones_application.utils.file_dialogs.backends.portal.variant import Variant

SUCCESS_CODE: Final[int] = 0
URIS_RESULT: Final[str] = "uris"
CURRENT_FILTER_RESULT: Final[str] = "current_filter"


@dataclass(frozen=True)
class ChooserResult:
    """
    What a file-chooser dialog answered with.

    ``uris`` carries the chosen locations in the dialog's own order. ``filter_label`` is the
    label of the type its selector stood on, present for a portal implementation that reports
    the selection.
    """

    uris: Tuple[str, ...]
    filter_label: Optional[str]

    @classmethod
    def from_response(cls, response: Message) -> Optional[Self]:
        """
        Reads what a dialog answered from the response signal carrying it.

        Args:
            response: The ``Response`` signal the portal delivers on a request's object path.

        Returns:
            Optional[Self]: What the dialog answered, ``None`` for a code other than success,
                which is how the portal reports a dismissal.
        """
        code, results = cast(Tuple[int, Dict[str, Variant]], response.body)
        if code != SUCCESS_CODE:
            return None

        return cls(
            uris=cls._uris(results),
            filter_label=cls._filter_label(results),
        )

    @staticmethod
    def _uris(results: Dict[str, Variant]) -> Tuple[str, ...]:
        uris = results.get(URIS_RESULT)
        if uris is None:
            return ()

        return tuple(cast(List[str], uris[1]))

    @staticmethod
    def _filter_label(results: Dict[str, Variant]) -> Optional[str]:
        """The label of the type the dialog stood on, as the portal reports the whole filter back."""
        reported = results.get(CURRENT_FILTER_RESULT)
        if reported is None:
            return None

        label, _patterns = cast(Tuple[str, List[Tuple[int, str]]], reported[1])
        return label
