from typing import Any, Dict, Final, List

import pytest
from pydantic import ValidationError

from assets.footage.specification import Footage, Listening, Timeline
from sampletones_core.constants.enums import AudioSourceType

SEGMENTS: Final[List[Dict[str, Any]]] = [
    {"from": 1.0, "audio": "original", "stems": ["Vocals", "Drums"]},
    {"from": 2.0, "audio": "reconstruction", "stems": ["Drums", "Vocals"]},
]


class TestTimeline:
    def test_a_segment_listens_to_its_source_and_stems_whatever_their_order(self) -> None:
        timeline = Timeline.model_validate({"start": 1.0, "end": 3.0, "segments": SEGMENTS})

        assert timeline.segments[0].listening == Listening(AudioSourceType.ORIGINAL, ("Drums", "Vocals"))
        assert timeline.segments[1].listening.stems == timeline.segments[0].listening.stems

    def test_the_first_segment_begins_at_the_start(self) -> None:
        with pytest.raises(ValidationError, match="first segment"):
            Timeline.model_validate({"start": 0.5, "end": 3.0, "segments": SEGMENTS})

    def test_segments_begin_in_increasing_order(self) -> None:
        with pytest.raises(ValidationError, match="increasing order"):
            Timeline.model_validate({"start": 1.0, "end": 3.0, "segments": [SEGMENTS[0], SEGMENTS[0]]})

    def test_the_timeline_ends_after_its_last_segment_begins(self) -> None:
        with pytest.raises(ValidationError, match="must end"):
            Timeline.model_validate({"start": 1.0, "end": 2.0, "segments": SEGMENTS})


class TestFootage:
    def test_a_footage_with_no_document_films_the_demo_piece(self) -> None:
        footage = Footage.model_validate(
            {"document": None, "frame_rate": 60, "timeline": {"start": 1.0, "end": 3.0, "segments": SEGMENTS}}
        )

        assert footage.document is None

    def test_the_frame_rate_is_positive(self) -> None:
        with pytest.raises(ValidationError):
            Footage.model_validate(
                {"document": None, "frame_rate": 0, "timeline": {"start": 1.0, "end": 3.0, "segments": SEGMENTS}}
            )
