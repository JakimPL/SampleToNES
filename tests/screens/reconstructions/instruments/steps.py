from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.reconstructions.instruments.constants import FADING
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import edit_envelope, marked, titled
from tests.suite.screens.steps.sequencer import open_voice
from tests.suite.screens.worlds.recordings import SONG, SONG_INSTRUMENT


def open_the_instrument(screen: Screen) -> None:
    """Opens the song's instrument from the Sequencer and waits for the Audition switch to appear."""
    instruments = screen.reconstructions.instruments
    open_voice(screen, SONG_INSTRUMENT)

    screen.expect(instruments.offers_audition, bool, description="the instrument open")


def song_title(screen: Screen, *, unsaved: bool) -> str:
    """The window title of the song, marked as unsaved or saved."""
    return titled(screen, marked(SONG.stem, unsaved=unsaved))


def give_it_a_volume(screen: Screen) -> None:
    """Opens the song's instrument and types the fading sequence into its Pulse 1 Volume field, leaving the
    project unsaved.
    """
    open_the_instrument(screen)
    edit_envelope(
        screen,
        channel=ChannelName.PULSE1,
        feature=FeatureKey.VOLUME,
        sequence=FADING,
        title=song_title(screen, unsaved=True),
    )
