import operator
from typing import Final

from automation.screen import Screen
from automation.vocabulary.playback import PLAY

NO_OUTPUT_TITLE: Final[str] = "global.dialog.title.no_audio_output"
NO_OUTPUT_MESSAGE: Final[str] = "global.dialog.message.no_audio_output"


def the_reader_is_told_no_sound_plays(screen: Screen) -> None:
    """Waits for the notice that no sound can play, reads its words, and dismisses it with OK.

    The Playback menu still offers Play, since nothing took the output.
    """
    notice = screen.no_output_notice
    screen.expect(notice.is_shown, bool, description="the notice that no sound can play")

    assert notice.prompt.title() == screen.words(NO_OUTPUT_TITLE)
    assert notice.words() == screen.words(NO_OUTPUT_MESSAGE)
    assert not screen.error_notice.is_shown()
    assert screen.sequencer.playback.play_entry() == screen.words(PLAY)

    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")
