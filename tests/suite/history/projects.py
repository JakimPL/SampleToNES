from pathlib import Path
from typing import Dict, Final, Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.project import Project
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.patterns.row import NoteCommand, Row
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from tests.suite.sequencer import sample_reconstruction
from tests.suite.stems import recorded_from, taking_turns_reconstruction

LEAD: Final[str] = "Lead"
BASS: Final[str] = "Bass"
PAD: Final[str] = "Pad"
PLUCK: Final[str] = "Pluck"

EVERY_PART_TITLE: Final[str] = "Every part"
EVERY_PART_AUTHOR: Final[str] = "History"
EVERY_PART_COMMENT: Final[str] = "Each part a gesture can reach."
EVERY_PART_ROWS: Final[int] = 8
EVERY_PART_TEMPO: Final[int] = 140
EVERY_PART_SPEED: Final[int] = 5
EVERY_PART_FIRST_HIGHLIGHT: Final[int] = 2
EVERY_PART_SECOND_HIGHLIGHT: Final[int] = 8

FIRST_PATTERN: Final[int] = 0
SECOND_PATTERN: Final[int] = 1

EVERY_PART_FILENAME: Final[str] = "every-part.stp"

LEAD_RECORDINGS: Final[Tuple[Path, Path]] = (Path("lead-a.wav"), Path("lead-b.wav"))
BASS_RECORDINGS: Final[Tuple[Path, Path]] = (Path("bass-a.wav"), Path("bass-b.wav"))


def lead_reconstruction() -> Reconstruction:
    """Two recordings taking turns on pulse 1, the second holding pulse 2 alone, so a removal applies."""
    reconstruction = taking_turns_reconstruction(LEAD_RECORDINGS)
    reconstruction = reconstruction.detached()
    return reconstruction


def bass_reconstruction() -> Reconstruction:
    """Two recordings each playing the triangle and the noise in turn."""
    reconstruction = recorded_from(
        sample_reconstruction([ChannelName.TRIANGLE, ChannelName.NOISE]),
        BASS_RECORDINGS,
    )
    reconstruction = reconstruction.detached()
    return reconstruction


def pad_instrument() -> Instrument:
    return Instrument(
        name=PAD,
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 12, 9, 6)),
            arpeggio=Envelope[int](items=(0, 4, 7), loop_point=0),
        ),
        initial_pitch=57,
    )


def pluck_instrument() -> Instrument:
    return Instrument(
        name=PLUCK,
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 8, 4, 0)),
            duty_cycle=Envelope[int](items=(2, 1)),
        ),
        initial_period=3,
    )


def _row(
    command: Optional[NoteCommand] = None,
    pitch: Optional[RowPitch] = None,
    volume: Optional[int] = None,
) -> Row:
    return Row(command=command, pitch=pitch, volume=volume)


def _write(
    project: Project,
    channel_name: ChannelName,
    pattern_index: int,
    rows: Dict[int, Row],
) -> None:
    channel = project.song.channels[channel_name]
    channel.ensure_pattern(pattern_index, project.song.rows_per_pattern)
    for row_index, row in rows.items():
        channel.set_row(pattern_index, row_index, row)


def every_part_project() -> Project:
    """A small project holding something in every part a history gesture can reach.

    Two samples carry two recordings each, so a channel edit, a stem removal and a retune all
    apply, and two instruments carry envelopes. The song plays three frames whose patterns name
    every voice through notes, steps, volumes and note-offs, and the settings and the
    properties all differ from a new project's.
    """
    project = Project.create(
        title=EVERY_PART_TITLE,
        author=EVERY_PART_AUTHOR,
        comment=EVERY_PART_COMMENT,
        rows_per_pattern=EVERY_PART_ROWS,
        settings=ProjectSettings(
            tempo=EVERY_PART_TEMPO,
            speed=EVERY_PART_SPEED,
            first_highlight=EVERY_PART_FIRST_HIGHLIGHT,
            second_highlight=EVERY_PART_SECOND_HIGHLIGHT,
        ),
    )
    lead = Sample(name=LEAD, reconstruction=lead_reconstruction())
    bass = Sample(name=BASS, reconstruction=bass_reconstruction())
    pad = pad_instrument()
    pluck = pluck_instrument()
    for voice in (lead, pad, bass, pluck):
        project.voices.append(voice)

    _write(
        project,
        ChannelName.PULSE1,
        FIRST_PATTERN,
        {
            0: _row(NoteOn(voice_id=lead.id), Note(value=60), 12),
            2: _row(pitch=Step(value=3)),
            4: _row(NoteOff()),
            6: _row(NoteOn(voice_id=pad.id), Note(value=64), 9),
        },
    )
    _write(
        project,
        ChannelName.PULSE1,
        SECOND_PATTERN,
        {
            0: _row(NoteOn(voice_id=lead.id), Step(value=-2), 8),
            3: _row(volume=4),
        },
    )
    _write(
        project,
        ChannelName.PULSE2,
        FIRST_PATTERN,
        {
            0: _row(NoteOn(voice_id=pluck.id), Note(value=67)),
            5: _row(NoteOff()),
        },
    )
    _write(
        project,
        ChannelName.TRIANGLE,
        FIRST_PATTERN,
        {
            0: _row(NoteOn(voice_id=bass.id), Note(value=45)),
            4: _row(pitch=Step(value=5)),
        },
    )
    _write(
        project,
        ChannelName.NOISE,
        FIRST_PATTERN,
        {
            0: _row(NoteOn(voice_id=bass.id)),
            2: _row(NoteOn(voice_id=pluck.id), Note(value=5), 10),
        },
    )
    project.song.order[0][ChannelName.NOISE] = None
    project.song.order.append(
        {
            ChannelName.PULSE1: SECOND_PATTERN,
            ChannelName.PULSE2: FIRST_PATTERN,
            ChannelName.TRIANGLE: None,
            ChannelName.NOISE: FIRST_PATTERN,
        }
    )
    project.song.order.append(
        {
            ChannelName.PULSE1: FIRST_PATTERN,
            ChannelName.PULSE2: None,
            ChannelName.TRIANGLE: FIRST_PATTERN,
            ChannelName.NOISE: FIRST_PATTERN,
        }
    )
    return project


def write_every_part_project(path: Path) -> Path:
    """Saves the every-part project where ``path`` names, the file a session opens."""
    ProjectContainer.save(every_part_project(), path)
    return path


@pytest.fixture
def every_part_file(tmp_path: Path) -> Path:
    """The every-part project saved to a file of its own, ready to open."""
    return write_every_part_project(tmp_path / EVERY_PART_FILENAME)
