from automation.screen import Screen
from automation.views.waveform import Waveform


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
