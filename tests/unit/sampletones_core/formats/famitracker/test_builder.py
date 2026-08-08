import numpy as np
import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.formats.famitracker.builder import (
    build_instrument_table,
    project_to_module,
)
from sampletones_core.formats.famitracker.specification.channels import (
    CHANNEL_COUNT_2A03,
    ChannelId,
)
from sampletones_core.formats.famitracker.specification.instruments import (
    MAX_INSTRUMENTS,
)
from sampletones_core.formats.famitracker.specification.parameters import (
    EXPANSION_NONE,
    Machine,
)
from sampletones_core.formats.famitracker.specification.patterns import (
    EMPTY_INSTRUMENT,
    NoteValue,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    LOOP_FROM_START,
    NO_LOOP_POINT,
    SequenceKind,
)
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project

from .conftest import RECONSTRUCTION_LENGTH, ProjectFixture, build_reconstruction

LEAD_PITCH = 60
OCTAVE = 12


class TestBuildInstrumentTable:
    def test_one_instrument_per_generator_slice(self, project_fixture: ProjectFixture) -> None:
        instruments, slots = build_instrument_table(project_fixture.project)
        # lead (pulse) + pad (pulse) + drum (noise) + bell (pulse + triangle) = 5
        assert len(instruments) == 5

    def test_slot_maps_sample_and_generator_to_index(self, project_fixture: ProjectFixture) -> None:
        _, slots = build_instrument_table(project_fixture.project)
        assert slots[(project_fixture.lead.id, GeneratorName.PULSE1)].index == 0
        assert slots[(project_fixture.bell.id, GeneratorName.TRIANGLE)].index == 4

    def test_slot_carries_initial_pitch(self, project_fixture: ProjectFixture) -> None:
        _, slots = build_instrument_table(project_fixture.project)
        assert slots[(project_fixture.lead.id, GeneratorName.PULSE1)].initial_pitch == LEAD_PITCH

    def test_slot_keeps_its_pitch_after_an_arpeggio_edit(self, project_fixture: ProjectFixture) -> None:
        """A pattern row triggers the instrument at the note its sample was reconstructed at.

        Raising a channel's first frame an octave moves the arpeggio sequence, and the row
        keeps naming the reference pitch — so the tracker plays the contour the reconstruction
        view sounds.
        """
        arpeggiated = [
            PulseInstruction(on=True, pitch=LEAD_PITCH + OCTAVE, volume=15, duty_cycle=0),
            PulseInstruction(on=True, pitch=LEAD_PITCH, volume=8, duty_cycle=0),
        ]
        project_fixture.lead.reconstruction.update_generator_data(
            GeneratorName.PULSE1,
            arpeggiated,
            np.ones(RECONSTRUCTION_LENGTH, dtype=np.float32),
            LEAD_PITCH,
        )

        instruments, slots = build_instrument_table(project_fixture.project)

        slot = slots[(project_fixture.lead.id, GeneratorName.PULSE1)]
        assert slot.initial_pitch == LEAD_PITCH
        assert list(instruments[slot.index].sequences[SequenceKind.ARPEGGIO].items)[0] == OCTAVE

    def test_looping_sample_loops_populated_sequences(self, project_fixture: ProjectFixture) -> None:
        instruments, slots = build_instrument_table(project_fixture.project)
        pad_index = slots[(project_fixture.pad.id, GeneratorName.PULSE1)].index
        pad = instruments[pad_index]
        assert pad.sequences[SequenceKind.VOLUME].loop_point == LOOP_FROM_START

    def test_non_looping_sample_leaves_loop_disabled(self, project_fixture: ProjectFixture) -> None:
        instruments, slots = build_instrument_table(project_fixture.project)
        lead_index = slots[(project_fixture.lead.id, GeneratorName.PULSE1)].index
        assert instruments[lead_index].sequences[SequenceKind.VOLUME].loop_point == NO_LOOP_POINT

    def test_exceeding_max_instruments_raises(self) -> None:
        project = Project.create()
        for number in range(MAX_INSTRUMENTS + 1):
            instructions = [PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)]
            reconstruction = build_reconstruction({GeneratorName.PULSE1: instructions})
            project.samples.append(Sample(name=f"sample-{number}", reconstruction=reconstruction))
        with pytest.raises(ValueError):
            build_instrument_table(project)


class TestProjectToModuleParameters:
    def test_expansion_and_channel_count(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert module.parameters.expansion_chip == EXPANSION_NONE
        assert module.parameters.channel_count == CHANNEL_COUNT_2A03

    def test_machine_and_engine_speed_from_default_frequency(self, project_fixture: ProjectFixture) -> None:
        # default nes_frequency is 30 -> NTSC with an explicit engine-speed override
        module = project_to_module(project_fixture.project)
        assert module.parameters.machine == Machine.NTSC
        assert module.parameters.engine_speed == project_fixture.project.settings.nes_frequency

    def test_information_and_comment_carry_through(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert module.information.title == "Demo"
        assert module.information.author == "Tester"
        assert module.comment == "a comment"

    def test_track_timing_from_settings(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        settings = project_fixture.project.settings
        assert module.track.speed == settings.speed
        assert module.track.tempo == settings.tempo
        assert module.track.rows_per_pattern == project_fixture.project.song.rows_per_pattern


class TestProjectToModulePatterns:
    def _pattern(self, module_patterns, channel: ChannelId, index: int):
        return next(p for p in module_patterns if p.channel == channel and p.index == index)

    def test_only_non_empty_patterns_emitted(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        channels = {pattern.channel for pattern in module.track.patterns}
        assert channels == {ChannelId.SQUARE1, ChannelId.NOISE}

    def test_instrument_row_resolves_note_and_volume(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        first = next(row for row in pattern.rows if row.row_number == 0)
        # initial_pitch 60 + transpose 0 -> C-3 (note 1, octave 3)
        assert first.note == 1
        assert first.octave == 3
        assert first.instrument == 0
        assert first.volume == 10

    def test_note_off_becomes_halt(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        halt = next(row for row in pattern.rows if row.row_number == 2)
        assert halt.note == int(NoteValue.HALT)
        assert halt.instrument == EMPTY_INSTRUMENT

    def test_volume_only_row_keeps_empty_note_and_instrument(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        volume_only = next(row for row in pattern.rows if row.row_number == 4)
        assert volume_only.note == int(NoteValue.NONE)
        assert volume_only.instrument == EMPTY_INSTRUMENT
        assert volume_only.volume == 5

    def test_empty_rows_are_dropped(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        assert {row.row_number for row in pattern.rows} == {0, 2, 4}

    def test_noise_row_uses_period_note(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.NOISE, 0)
        first = next(row for row in pattern.rows if row.row_number == 0)
        # period 4 -> note 5, octave 0
        assert first.note == 5
        assert first.octave == 0


class TestProjectToModuleOrder:
    def test_order_has_one_entry_per_channel(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert len(module.track.order) == 2
        assert all(len(frame) == CHANNEL_COUNT_2A03 for frame in module.track.order)

    def test_referenced_patterns_appear_in_order(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        first_frame = module.track.order[0]
        assert first_frame[ChannelId.SQUARE1] == 0
        assert first_frame[ChannelId.NOISE] == 0

    def test_none_slots_map_to_a_reserved_pattern_index(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        second_frame = module.track.order[1]
        # every None slot resolves to a concrete uint8 index
        assert all(isinstance(index, int) and index >= 0 for index in second_frame)

    def test_dpcm_channel_is_always_empty(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert all(frame[ChannelId.DPCM] == 0 for frame in module.track.order)
