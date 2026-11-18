from automation.screen import Screen
from automation.views.waveform import Waveform
from tests.screens.reconstructions.player.constants import STILL_FRAMES


def entry(screen: Screen) -> str:
    """What the Playback menu's first entry reads: Play while stopped, Pause while playing, Resume while paused."""
    return screen.sequencer.playback.play_entry()


def expect_entry(screen: Screen, key: str) -> None:
    """Waits until the Playback menu's first entry reads the words of ``key``."""
    screen.expect(lambda: entry(screen), screen.words(key).__eq__, description=f"the Playback menu reading {key}")


def advancing(screen: Screen, waveform: Waveform, after: float) -> float:
    """Waits until the cursor stands past sample ``after`` and returns where it stands."""
    return screen.expect(
        lambda: waveform.cursor() or -1.0,
        lambda reading: reading > after,
        description=f"the cursor moving past sample {after:.0f}",
    )


def cursor(waveform: Waveform) -> float:
    """The cursor's sample on the waveform, which must be drawn."""
    found = waveform.cursor()
    assert found is not None, "no cursor stands on the waveform"
    return found


def held_still(screen: Screen, waveform: Waveform) -> float:
    """The cursor's sample, read twice some frames apart and found the same."""
    standing = cursor(waveform)
    screen.frames(STILL_FRAMES)
    assert waveform.cursor() == standing
    return standing
