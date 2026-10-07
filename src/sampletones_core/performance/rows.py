from typing import Optional

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import transposed_reference
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.project.patterns.pitch import RowPitch, step_of
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import (
    VoiceLookup,
    VoiceUnion,
    voice_channels,
    voice_reference,
)


def resolve_row(
    song: Song,
    position: SongPosition,
    channel_name: ChannelName,
) -> Optional[Row]:
    """The row one channel reaches at a position in the order.

    A position answers with a row where the order plays a pattern on that channel and the
    pattern is long enough to hold the row; anywhere else the channel plays on with whatever
    it already carries.

    Args:
        song: The arrangement being played.
        position: The order frame and the row within it.
        channel_name: The channel whose pattern is read.

    Returns:
        Optional[Row]: The row the channel reaches, or ``None`` where it reaches none.
    """
    if position.order_position >= song.order_length():
        return None

    order_entry = song.order[position.order_position].get(channel_name)
    if order_entry is None:
        return None

    pattern = song.pattern(channel_name, order_entry)
    if pattern is None or position.row_index >= len(pattern.rows):
        return None

    return pattern.rows[position.row_index]


def sounding_voice(
    performance: ChannelPerformance,
    channel_name: ChannelName,
    voices: VoiceLookup,
) -> Optional[VoiceUnion]:
    """The voice a channel is sounding, and ``None`` while the channel is silent.

    A channel sounds while it carries a voice the project holds that has frames on the channel. A
    voice that has played its frames out is still the channel's note, since no row has ended it, so
    the channel goes on sounding it in these terms until a note-off or another note.

    Args:
        performance: What the channel carries.
        channel_name: The channel being read.
        voices: Where a voice id resolves to the voice it names.

    Returns:
        Optional[VoiceUnion]: The voice sounding, or ``None`` on a silent channel.
    """
    if performance.voice_id is None:
        return None

    voice = voices(performance.voice_id)
    if voice is None or channel_name not in voice_channels(voice):
        return None

    return voice


def sounding_pitch(
    performance: ChannelPerformance,
    channel_name: ChannelName,
    voices: VoiceLookup,
) -> Optional[int]:
    """The pitch, or the period, a channel is sounding, and ``None`` while it is silent.

    The voice sounds where its reference and the transpose in force put it, which is the note the
    channel plays before any arpeggio the voice writes.

    Args:
        performance: What the channel carries.
        channel_name: The channel being read.
        voices: Where a voice id resolves to the voice it names.

    Returns:
        Optional[int]: The pitch the channel sounds, or ``None`` on a silent channel.
    """
    voice = sounding_voice(performance, channel_name, voices)
    if voice is None:
        return None

    return transposed_reference(
        channel_name,
        voice_reference(voice, channel_name),
        performance.transpose,
    )


def note_step(
    pitch: Optional[RowPitch],
    voice: VoiceUnion,
    channel_name: ChannelName,
    *,
    sounding: Optional[int],
) -> Optional[int]:
    """The step a note-on starts a voice at, and ``None`` where the row starts nothing.

    A row stating a pitch starts the voice there. A sample stating none plays as it was recorded.
    An instrument stating none goes on from the pitch the channel is sounding, whichever voice
    sounded it, which is what lets a row restart the envelopes under a note already standing; on
    a silent channel it has no pitch to sound and starts nothing.

    Args:
        pitch: The pitch the row states, or ``None`` for an empty cell.
        voice: The voice the row names.
        channel_name: The channel the row stands on.
        sounding: The pitch the channel is sounding, or ``None`` while it is silent.

    Returns:
        Optional[int]: The step from the voice's reference, or ``None`` where nothing starts.
    """
    reference = voice_reference(voice, channel_name)
    if pitch is not None:
        return step_of(pitch, reference=reference)

    match voice:
        case Sample():
            return 0
        case Instrument():
            if sounding is None:
                return None

            return sounding - reference


def apply_row(
    performance: ChannelPerformance,
    row: Row,
    channel_name: ChannelName,
    voices: VoiceLookup,
) -> bool:
    """Moves a channel onto the row it has reached, and reports whether the note starts over.

    A note column names the voice to sound and begins it at the step :func:`note_step` gives the
    row, taking the volume the row states or the full level where it states none, with every
    envelope dimension at the value a song starts on. A row naming no note leaves the voice playing
    and changes only the columns it fills in: a pitch moves the note already sounding, measured
    from that voice's own reference, and a volume sets its level. A voice the project no longer
    holds starts as a silent note, so the rows that named it rest while the rows around them play.

    Args:
        performance: What the channel carries; updated in place.
        row: The row the channel reached.
        channel_name: The channel the row stands on.
        voices: Where a voice id resolves to the voice it names.

    Returns:
        bool: Whether the channel starts over, which is where a phase-continuous voice resets.
    """
    match row.command:
        case NoteOn() as note_on:
            voice = voices(note_on.voice_id)
            step = (
                0
                if voice is None
                else note_step(
                    row.pitch,
                    voice,
                    channel_name,
                    sounding=sounding_pitch(performance, channel_name, voices),
                )
            )
            if step is None:
                return False

            performance.start_note(
                note_on.voice_id,
                transpose=step,
                volume=row.volume if row.volume is not None else MAX_VOLUME,
            )
            return True
        case NoteOff():
            performance.voice_id = None
            performance.tick_index = 0
            return True
        case None:
            if row.pitch is not None:
                _bend(performance, row.pitch, channel_name, voices)

            if row.volume is not None:
                performance.volume = row.volume

            return False


def _bend(
    performance: ChannelPerformance,
    pitch: RowPitch,
    channel_name: ChannelName,
    voices: VoiceLookup,
) -> None:
    """Moves the note a channel is sounding to a pitch, leaving a silent channel as it is."""
    voice = sounding_voice(performance, channel_name, voices)
    if voice is None:
        return

    performance.transpose = step_of(pitch, reference=voice_reference(voice, channel_name))
