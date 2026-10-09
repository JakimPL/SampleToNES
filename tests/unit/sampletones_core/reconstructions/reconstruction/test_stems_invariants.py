from dataclasses import dataclass
from typing import Callable, Final, FrozenSet, List, Mapping, Sequence

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.features import resting_reference
from sampletones_core.instructions import InstructionData, InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
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
from tests.suite.stems import RECORDED_SCALE

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
EVERY_STEM: Final[FrozenSet[int]] = frozenset({STEM_A, STEM_B})
UNHELD_STEM_IDS: Final[FrozenSet[int]] = frozenset({RESTING_STEM_ID, AUTHORED_STEM_ID})
STORED_ID: Final[str] = "stored"


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
            scale=RECORDED_SCALE,
        ),
    )


def _stored(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    owners: Mapping[ChannelName, Sequence[int]],
) -> Reconstruction:
    """A document built from its stored parts as they stand, the way a file states them.

    Creating a document settles it, so a record naming a channel the streams leave silent is
    one a stored file carries and creation never writes.
    """
    return Reconstruction(
        id=STORED_ID,
        config=Config(),
        instructions_data=[
            InstructionsItem(
                channel_name=channel_name,
                instructions=[
                    InstructionData.create(instruction) for instruction in instructions.get(channel_name, ())
                ],
                initial_pitch=resting_reference(channel_name),
                held_features=[],
            )
            for channel_name in ChannelName.items()
        ],
        stems_data=StemsData(
            config=_stems_config(),
            assignments=[
                ChannelAssignment(channel_name=channel_name, stem_ids=list(stem_ids))
                for channel_name, stem_ids in owners.items()
            ],
            scale=RECORDED_SCALE,
        ),
        coefficient=1.0,
    )


def _edited(reconstruction: Reconstruction, instructions: List[InstructionUnion]) -> Reconstruction:
    edited = reconstruction.model_copy(deep=True)
    edited = edited.with_channel_data(
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
            label="an edit writing every frame silent",
            gesture=lambda reconstruction: _edited(reconstruction, [PulseInstruction.null_instruction()] * 3),
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
            label="a removal leaving a channel only rests",
            gesture=lambda reconstruction: without_stem(
                _edited(
                    reconstruction,
                    [PulseInstruction.null_instruction(), _pulse(62), PulseInstruction.null_instruction()],
                ),
                STEM_B,
            ),
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
    detached = detached.detached()
    return detached


class TestARecordTheDocumentRefuses:
    def test_a_channel_in_play_naming_no_owner_per_frame_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _stored(
                {ChannelName.PULSE1: [_pulse(60), _pulse(62)]},
                {ChannelName.PULSE1: [STEM_A]},
            )

    def test_a_frame_naming_a_recording_the_setup_leaves_out_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _stored(
                {ChannelName.NOISE: [_noise()]},
                {ChannelName.NOISE: [STEM_B]},
            )

    def test_a_sounding_frame_recorded_as_resting_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _stored(
                {ChannelName.PULSE1: [_pulse(60)]},
                {ChannelName.PULSE1: [RESTING_STEM_ID]},
            )

    def test_a_silent_frame_recorded_as_held_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _stored(
                {ChannelName.PULSE1: [_pulse(60), PulseInstruction.null_instruction()]},
                {ChannelName.PULSE1: [STEM_A, STEM_A]},
            )

    def test_a_channel_standing_by_carrying_a_record_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _stored(
                {ChannelName.PULSE1: [_pulse(60)]},
                {ChannelName.PULSE1: [STEM_A], ChannelName.TRIANGLE: [RESTING_STEM_ID]},
            )

    def test_a_channel_resting_through_every_frame_is_refused(self) -> None:
        """A channel resting throughout stands by, so a stream stating those frames is refused."""
        with pytest.raises(ValidationError):
            _stored(
                {
                    ChannelName.PULSE1: [_pulse(60)],
                    ChannelName.NOISE: [NoiseInstruction.null_instruction()] * 2,
                },
                {
                    ChannelName.PULSE1: [STEM_A],
                    ChannelName.NOISE: [RESTING_STEM_ID] * 2,
                },
            )


class TestWhatCreatingSettles:
    """A conversion hands every channel it covered a stream, and a silent one stands by."""

    @pytest.fixture
    def created(self) -> Reconstruction:
        """Stem A sounding the pulse while the noise it also covers rests through every frame."""
        return _reconstruction(
            {
                ChannelName.PULSE1: [_pulse(60), _pulse(62)],
                ChannelName.NOISE: [NoiseInstruction.null_instruction()] * 2,
            },
            {
                ChannelName.PULSE1: [STEM_A, STEM_A],
                ChannelName.NOISE: [RESTING_STEM_ID] * 2,
            },
        )

    def test_a_channel_resting_through_every_frame_stands_by(self, created: Reconstruction) -> None:
        assert created.playing_channels == (ChannelName.PULSE1,)
        assert created.streams[ChannelName.NOISE] == InstructionsItem.resting(ChannelName.NOISE)

    def test_the_record_names_it_no_more(self, created: Reconstruction) -> None:
        assert ChannelName.NOISE not in created.stems_data.assignments_by_channel

    def test_a_conversion_where_nothing_sounds_stands_every_channel_by(self) -> None:
        created = _reconstruction(
            {ChannelName.PULSE1: [PulseInstruction.null_instruction()]},
            {ChannelName.PULSE1: [RESTING_STEM_ID]},
        )

        assert created.playing_channels == ()
        assert created.stems_data.assignments == ()


class TestARecordingHoldingNoFrame:
    """A recording holding no frame leaves the document, unless no recording holds one at all."""

    def test_a_recording_the_picker_never_chose_leaves(self) -> None:
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60)]},
            {ChannelName.PULSE1: [STEM_A]},
        )

        assert [entry.id for entry in reconstruction.stems_data.config.entries] == [STEM_A]
        assert reconstruction.stems_data.config.hierarchy.levels == ((STEM_A,),)

    def test_a_recording_an_edit_emptied_leaves(self, reconstruction: Reconstruction) -> None:
        edited = _edited(
            reconstruction,
            [_pulse(60), PulseInstruction.null_instruction(), PulseInstruction.null_instruction()],
        )

        assert [entry.id for entry in edited.stems_data.config.entries] == [STEM_A]
        assert STEM_B not in edited.stems_data.assignments_by_channel[ChannelName.PULSE1]

    def test_a_record_where_nothing_sounds_keeps_every_recording(self) -> None:
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [PulseInstruction.null_instruction()]},
            {ChannelName.PULSE1: [RESTING_STEM_ID]},
        )

        assert [entry.id for entry in reconstruction.stems_data.config.entries] == [STEM_A, STEM_B]

    def test_an_edit_silencing_every_recording_keeps_them_all(self) -> None:
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60), _pulse(62)]},
            {ChannelName.PULSE1: [STEM_A, STEM_B]},
        )

        edited = _edited(reconstruction, [])

        assert [entry.id for entry in edited.stems_data.config.entries] == [STEM_A, STEM_B]

    def test_a_record_holding_only_the_readers_frames_keeps_every_recording(self) -> None:
        """Frames the reader wrote answer to no recording, so they tell none of them apart."""
        reconstruction = _reconstruction(
            {ChannelName.PULSE1: [_pulse(60), _pulse(62)]},
            {ChannelName.PULSE1: [STEM_A, STEM_B]},
        )

        authored = _edited(_edited(reconstruction, []), [_pulse(60)])

        assert authored.stems_data.assignments_by_channel == {ChannelName.PULSE1: (AUTHORED_STEM_ID,)}
        assert [entry.id for entry in authored.stems_data.config.entries] == [STEM_A, STEM_B]

    def test_a_stored_record_naming_an_idle_recording_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _stored(
                {ChannelName.PULSE1: [_pulse(60)]},
                {ChannelName.PULSE1: [STEM_A]},
            )
