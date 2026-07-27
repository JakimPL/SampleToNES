from sampletones_application.logic.project.title.compose import join_segments, window_title
from sampletones_shared.constants.symbols import TITLE_SEPARATOR


class TestJoinSegments:
    def test_joins_with_the_separator(self) -> None:
        assert join_segments("SampleToNES", "Song") == f"SampleToNES{TITLE_SEPARATOR}Song"

    def test_keeps_only_the_segments_with_text(self) -> None:
        assert join_segments("SampleToNES", "", "Song") == f"SampleToNES{TITLE_SEPARATOR}Song"

    def test_single_segment_stands_alone(self) -> None:
        assert join_segments("SampleToNES") == "SampleToNES"

    def test_empty_input_yields_empty_title(self) -> None:
        assert join_segments("", "") == ""


class TestWindowTitle:
    def test_application_name_leads_the_document(self) -> None:
        assert window_title("SampleToNES", "Song*") == f"SampleToNES{TITLE_SEPARATOR}Song*"

    def test_empty_document_leaves_the_application_name(self) -> None:
        assert window_title("SampleToNES", "") == "SampleToNES"
