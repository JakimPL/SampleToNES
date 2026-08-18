from sampletones_application.layout.general.dialogs.about import AboutDialogLayout


class TestTheRoomTheTextTakes:
    def test_the_text_wraps_in_what_the_mark_leaves(self) -> None:
        layout = AboutDialogLayout(width=480, height=210, logo=72, padding=40)
        assert layout.text_wrap == 368
