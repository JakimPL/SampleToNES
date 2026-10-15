from dataclasses import dataclass
from typing import Callable, Optional

from sampletones_application.view_model.sequencer.voices import VoiceKind

from .key import Keyboard, LiveKey
from .sound import LiveSound

StrikeFollower = Callable[[Optional[int]], None]


def release_ends_note(keyboard: Keyboard, kind: VoiceKind) -> bool:
    """Whether lifting a key of ``keyboard`` ends the note of a voice of ``kind`` it struck.

    An instrument sounds for as long as its key is down, on either keyboard. A recording is a take of its
    own, so a computer key plays it to its end, and a MIDI key, which plays a voice as a held note, ends it
    as it lifts.
    """
    match kind:
        case VoiceKind.INSTRUMENT:
            return True
        case VoiceKind.SAMPLE:
            return keyboard is Keyboard.MIDI


@dataclass(frozen=True, eq=False)
class Strike:
    """One press of a key and what it sounds.

    Each press is a strike of its own, compared by identity, so a key pressed again strikes again and a key
    returned to strikes its own press once more.

    Attributes:
        key: The key pressed.
        sound: What the press sounds.
        follower: What hears where the press's note stands in its voice's samples while it sounds, and ``None``
            once it sounds no more, on the render thread; ``None`` for a press nothing follows.
    """

    key: LiveKey
    sound: LiveSound
    follower: Optional[StrikeFollower]

    @property
    def ends_on_release(self) -> bool:
        """Whether lifting the key ends the note, as :func:`release_ends_note` decides for its keyboard and voice."""
        return release_ends_note(self.key.keyboard, self.sound.kind)
