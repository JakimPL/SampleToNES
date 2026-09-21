from dataclasses import dataclass
from typing import Callable, Final, FrozenSet, List, Mapping, Sequence

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.removal import without_stem
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
EVERY_STEM: Final[FrozenSet[int]] = frozenset({STEM_A, STEM_B})
UNHELD_STEM_IDS: Final[FrozenSet[int]] = frozenset({RESTING_STEM_ID, AUTHORED_STEM_ID})


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _noise() -> NoiseInstruction:
    return NoiseInstruction(on=True, period=4, volume=8, short=False)


def _stems_config() -> StemsConfig:
    """Stem A over the first pulse and the noise, stem B over the first pulse alone."""
    return StemsConfig(
        entries=[
            StemEntry(
                id=STEM_A,
                settings=StemSettings(
                    channels=[ChannelName.PULSE1, ChannelName.NOISE],
                    bends=bending_channels([ChannelName.PULSE1, ChannelName.NOISE]),
                    channel_cap=1,
                ),
            ),
            StemEntry(
                id=STEM_B,
                settings=StemSettings(
                    channels=[ChannelName.PULSE1],
                    bends=bending_channels([ChannelName.PULSE1]),
                    channel_cap=1,
                ),
            ),
        ],
        hierarchy=StemsHierarchy(levels=[[STEM_A], [STEM_B]]),
    )


def _reconstruction(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    owners: Mapping[ChannelName, Sequence[int]],
) -> Reconstruction:
    return Reconstruction.create(
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=(),
        stems_data=StemsData(
            config=_stems_config(),
            assignments=[
                ChannelAssignment(channel_name=channel_name, stem_ids=list(stem_ids))
                for channel_name, stem_ids in owners.items()
            ],
        ),
    )


def _edited(reconstruction: Reconstruction, instructions: List[InstructionUnion]) -> Reconstruction:
    edited = reconstruction.model_copy(deep=True)
    edited.update_channel_data(
        ChannelName.PULSE1,
        instructions,
        initial_pitch=reconstruction.initial_pitches[ChannelName.PULSE1],
        held_features=reconstruction.held_features[ChannelName.PULSE1],
        heard=EVERY_STEM,
    )
    return edited


@pytest.fixture
def reconstruction() -> Reconstruction:
    """Two recordings over the pulse, stem A alone on the noise, one frame resting on each."""
    return _reconstruction(
        {
            ChannelName.PULSE1: [_pulse(60), _pulse(62), PulseInstruction.null_instruction()],
            ChannelName.NOISE: [_noise(), _noise(), NoiseInstruction.null_instruction()],
        },
        {
            ChannelName.PULSE1: [STEM_A, STEM_B, RESTING_STEM_ID],
            ChannelName.NOISE: [STEM_A, STEM_A, RESTING_STEM_ID],
        },
    )


def _assert_record_holds(reconstruction: Reconstruction) -> None:
    """Every rule the per-frame record keeps, asserted together.

    The record answers for the channels in play and for those alone; each frame names an
    owner the setup knows, rest and silence name the same frames, and a recording holds only
    the channels its own settings occupy.
    """
    stems_data = reconstruction.stems_data
    recorded = frozenset(stems_data.config.entries_by_id)
    owned = stems_data.assignments_by_channel

    assert frozenset(owned) == frozenset(reconstruction.playing_channels)

    for channel_name in reconstruction.playing_channels:
        instructions = reconstruction.instructions[channel_name]
        stem_ids = owned[channel_name]
        assert len(stem_ids) == len(instructions)

        for instruction, stem_id in zip(instructions, stem_ids):
            assert stem_id in recorded | UNHELD_STEM_IDS
            assert (stem_id == RESTING_STEM_ID) == (not instruction.on)
            if stem_id in recorded:
                assert channel_name in stems_data.config.entries_by_id[stem_id].settings.channel_set


class TestTheRecordAfterEveryGesture(BaseTestSuite):
    """Whatever a reader does to a document, the per-frame record still answers for it."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        gesture: Callable[[Reconstruction], Reconstruction]

    test_cases = (
        TestCase(
            label="a document straight out of a conversion",
            gesture=lambda reconstruction: reconstruction,
        ),
        TestCase(
            label="an edit changing a frame a recording holds",
            gesture=lambda reconstruction: _edited(
                reconstruction,
                [_pulse(70), _pulse(62), PulseInstruction.null_instruction()],
            ),
        ),
        TestCase(
            label="an edit quieting a frame a recording holds",
            gesture=lambda reconstruction: _edited(
                reconstruction,
                [PulseInstruction.null_instruction(), _pulse(62), PulseInstruction.null_instruction()],
            ),
        ),
        TestCase(
            label="an edit writing into a resting frame",
            gesture=lambda reconstruction: _edited(reconstruction, [_pulse(60), _pulse(62), _pulse(64)]),
        ),
        TestCase(
            label="an edit lengthening the stream",
            gesture=lambda reconstruction: _edited(
                reconstruction,
                [_pulse(60), _pulse(62), _pulse(64), _pulse(66)],
            ),
        ),
        TestCase(
            label="an edit shortening the stream",
            gesture=lambda reconstruction: _edited(reconstruction, [_pulse(60)]),
        ),
        TestCase(
            label="an edit emptying the channel",
            gesture=lambda reconstruction: _edited(reconstruction, []),
        ),
        TestCase(
            label="an edit writing an emptied channel back into play",
            gesture=lambda reconstruction: _edited(_edited(reconstruction, []), [_pulse(60), _pulse(62)]),
        ),
        TestCase(
            label="a recording taken out",
            gesture=lambda reconstruction: without_stem(reconstruction, STEM_B),
        ),
        TestCase(
            label="a recording taken out after an edit",
            gesture=lambda reconstruction: without_stem(
                _edited(reconstruction, [_pulse(70), _pulse(72), _pulse(74)]),
                STEM_B,
            ),
        ),
        TestCase(
            label="a document detached from its recordings",
            gesture=lambda reconstruction: _detached(reconstruction),
        ),
        TestCase(
            label="a document through a round trip",
            gesture=lambda reconstruction: Reconstruction.deserialize(reconstruction.serialize()),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_record_answers_for_the_document(
        self,
        reconstruction: Reconstruction,
        test_case: TestCase,
    ) -> None:
        _assert_record_holds(test_case.gesture(reconstruction))


def _detached(reconstruction: Reconstruction) -> Reconstruction:
    detached = reconstruction.model_copy(deep=True)
    detached.detach_source()
    return detached


class TestARecordTheDocumentRefuses:
    def test_a_channel_in_play_naming_no_owner_per_frame_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _reconstruction(
                {ChannelName.PULSE1: [_pulse(60), _pulse(62)]},
                {ChannelName.PULSE1: [STEM_A]},
            )

    def test_a_frame_naming_a_recording_the_setup_leaves_out_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _reconstruction(
                {ChannelName.NOISE: [_noise()]},
                {ChannelName.NOISE: [STEM_B]},
            )

    def test_a_sounding_frame_recorded_as_resting_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _reconstruction(
                {ChannelName.PULSE1: [_pulse(60)]},
                {ChannelName.PULSE1: [RESTING_STEM_ID]},
            )

    def test_a_silent_frame_recorded_as_held_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _reconstruction(
                {ChannelName.PULSE1: [PulseInstruction.null_instruction()]},
                {ChannelName.PULSE1: [STEM_A]},
            )

    def test_a_channel_standing_by_carrying_a_record_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _reconstruction(
                {ChannelName.PULSE1: [_pulse(60)]},
                {ChannelName.PULSE1: [STEM_A], ChannelName.TRIANGLE: [RESTING_STEM_ID]},
            )


class TestAnEntryHoldingNoFrame:
    def test_a_recording_the_picker_never_chose_stays_on_the_record(self) -> None:
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60)]},
            {ChannelName.PULSE1: [STEM_A]},
        )

        assert [entry.id for entry in reconstruction.stems_data.config.entries] == [STEM_A, STEM_B]

    def test_a_recording_an_edit_emptied_stays_on_the_record(self, reconstruction: Reconstruction) -> None:
        edited = _edited(
            reconstruction,
            [_pulse(60), PulseInstruction.null_instruction(), PulseInstruction.null_instruction()],
        )

        assert [entry.id for entry in edited.stems_data.config.entries] == [STEM_A, STEM_B]
        assert STEM_B not in edited.stems_data.assignments_by_channel[ChannelName.PULSE1]
