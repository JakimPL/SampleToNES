from typing import Optional, Tuple

from sampletones_application.categories.elements.sequencer import SequencerTrackerElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
)
from sampletones_application.view_model.sequencer.voices import VoiceEntryViewModel, VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.patterns.row import NoteCommand
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.utils.display import display_pitch, display_voice_label
from sampletones_shared.utils.agreement import Agreement

Voices = Tuple[VoiceEntryViewModel, ...]


def _sample_command(cell: SequencerCellViewModel) -> Optional[NoteCommand]:
    """The command the sample column reads from a cell: a hand-written instrument reads as none there."""
    if cell.kind is VoiceKind.INSTRUMENT:
        return None

    return cell.command


class CellStatusText:
    """The sentence the status bar prints for the slot the pointer rests on.

    A slot is named by what it holds, in the terms the grid prints it in: a voice by its number
    and name, a pitch by the face it was typed in, a volume by its level, and an empty slot by its
    name alone. The sample column speaks for the channels its row spans, so a slot whose channels
    disagree says so, which is what the ``?`` it shows means.
    """

    def __init__(self, language_manager: LanguageManager) -> None:
        def label(element: SequencerTrackerElements) -> str:
            return language_manager[Page.SEQUENCER, Panel.TRACKER, TextType.LABEL, element]

        self._lbl_voice = label(SequencerTrackerElements.STATUS_VOICE)
        self._lbl_sample = label(SequencerTrackerElements.STATUS_SAMPLE)
        self._lbl_pitch = label(SequencerTrackerElements.STATUS_PITCH)
        self._lbl_volume = label(SequencerTrackerElements.STATUS_VOLUME)
        self._lbl_note_off = label(SequencerTrackerElements.STATUS_NOTE_OFF)
        self._lbl_different_voices = label(SequencerTrackerElements.STATUS_DIFFERENT_VOICES)
        self._lbl_different_pitches = label(SequencerTrackerElements.STATUS_DIFFERENT_PITCHES)
        self._lbl_different_volumes = label(SequencerTrackerElements.STATUS_DIFFERENT_VOLUMES)
        self._tpl_voice = language_manager["sequencer.tracker.template.status_voice"]
        self._tpl_sample = language_manager["sequencer.tracker.template.status_sample"]
        self._tpl_note = language_manager["sequencer.tracker.template.status_note"]
        self._tpl_period = language_manager["sequencer.tracker.template.status_period"]
        self._tpl_transpose = language_manager["sequencer.tracker.template.status_transpose"]
        self._tpl_volume = language_manager["sequencer.tracker.template.status_volume"]

    def describe(
        self,
        row: SequencerRowViewModel,
        channel: Optional[ChannelName],
        subcolumn: SubColumn,
        voices: Voices,
    ) -> str:
        """What one slot of a row holds, as the status bar says it.

        Args:
            row: The row the slot stands on.
            channel: The channel the slot belongs to, ``None`` for the sample column.
            subcolumn: Which of the three slots the pointer rests on.
            voices: The project's voices, in the order the voices list numbers them.

        Returns:
            str: The sentence.
        """
        match subcolumn:
            case SubColumn.VOICE:
                return self._voice(row, channel, voices)
            case SubColumn.TRANSPOSE:
                return self._pitch(row, channel)
            case SubColumn.VOLUME:
                return self._volume(row, channel)

    def _voice(
        self,
        row: SequencerRowViewModel,
        channel: Optional[ChannelName],
        voices: Voices,
    ) -> str:
        if channel is not None:
            return self._command(row.cells[channel].command, voices, self._tpl_voice, self._lbl_voice)

        commands = Agreement.collapse(_sample_command(row.cells[name]) for name in row.note_channels)
        if commands.is_mixed:
            return self._lbl_different_voices

        return self._command(commands.resolve(absent=None, mixed=None), voices, self._tpl_sample, self._lbl_sample)

    def _command(
        self,
        command: Optional[NoteCommand],
        voices: Voices,
        template: str,
        empty: str,
    ) -> str:
        """A voice slot's reading: the voice it names as the voices list prints it, a cut, or the slot's name."""
        match command:
            case NoteOff():
                return self._lbl_note_off
            case NoteOn():
                named = self._voice_label(voices, command.voice_id)
                return template.format(voice=named) if named is not None else empty
            case None:
                return empty

    @staticmethod
    def _voice_label(voices: Voices, voice_id: str) -> Optional[str]:
        """The label the voices list prints a voice under, and ``None`` for a voice the pool lacks."""
        for position, entry in enumerate(voices):
            if entry.voice_id == voice_id:
                return display_voice_label(position, entry.name)

        return None

    def _pitch(self, row: SequencerRowViewModel, channel: Optional[ChannelName]) -> str:
        if channel is not None:
            return self._face(row.cells[channel].pitch)

        pitches = Agreement.collapse(row.cells[name].pitch for name in row.offset_channels)
        if pitches.is_mixed:
            return self._lbl_different_pitches

        return self._face(pitches.resolve(absent=None, mixed=None))

    def _face(self, pitch: Optional[RowPitch]) -> str:
        """A pitch slot's reading in the face the cell shows: a step in decimal, a note by name, a period by number."""
        match pitch:
            case Step():
                return self._tpl_transpose.format(step=f"{pitch.value:+d}")
            case Note() if pitch.value <= MAX_PERIOD:
                return self._tpl_period.format(period=pitch.value)
            case Note():
                return self._tpl_note.format(note=display_pitch(pitch))
            case None:
                return self._lbl_pitch

    def _volume(self, row: SequencerRowViewModel, channel: Optional[ChannelName]) -> str:
        if channel is not None:
            return self._level(row.cells[channel].level)

        levels = Agreement.collapse(row.cells[name].level for name in row.offset_channels)
        if levels.is_mixed:
            return self._lbl_different_volumes

        return self._level(levels.resolve(absent=None, mixed=None))

    def _level(self, level: Optional[int]) -> str:
        if level is None:
            return self._lbl_volume

        return self._tpl_volume.format(volume=level)
