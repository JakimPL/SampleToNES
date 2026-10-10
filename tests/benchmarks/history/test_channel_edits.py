import copy
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.constants.general import BYTES_PER_MEGABYTE
from tests.suite.long_documents import turning_instructions
from tests.suite.memory import retained_bytes
from tests.suite.stems import single_entry_stems_data
from tests.suite.timing import seconds

DOCUMENT_FRAMES: Final[int] = 4_000
EDITS: Final[int] = 8
SHARE_MARGIN: Final[float] = 1.5
SAMPLE_NAME: Final[str] = "Long conversion"
EDITED_CHANNEL: Final[ChannelName] = ChannelName.PULSE1


@pytest.fixture(scope="module", name="document")
def document_fixture() -> Reconstruction:
    """A document shaped like a long conversion: every channel sounding, each frame an instruction of its own."""
    instructions = turning_instructions(DOCUMENT_FRAMES)
    return Reconstruction.create(
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=(Path("/dev/null"),),
        stems_data=single_entry_stems_data(ChannelName.items(), instructions),
    )


@pytest.fixture(name="arranged")
def arranged_fixture(
    controller: ProjectController,
    document: Reconstruction,
) -> ProjectController:
    """The project holding the document as its one sample."""
    controller.add_sample(document, SAMPLE_NAME)
    return controller


def _sample(controller: ProjectController) -> Sample:
    return next(voice for voice in controller.project.voices if isinstance(voice, Sample))


def _rebuilt_channel(
    reconstruction: Reconstruction,
    channel_name: ChannelName,
) -> List[InstructionUnion]:
    """The channel's instructions built anew, the way a rebuild hands back every frame of the channel it redraws."""
    return [instruction.model_copy() for instruction in reconstruction.instructions[channel_name]]


def _land(
    controller: ProjectController,
    history: HistoryManager,
    channel_name: ChannelName,
    instructions: List[InstructionUnion],
) -> None:
    sample = _sample(controller)
    live = sample.reconstruction
    updated = live.with_channel_data(
        channel_name,
        instructions,
        live.initial_pitches[channel_name],
        live.held_features[channel_name],
        heard=live.recorded_stem_ids,
    )
    with history.transaction(HistoryAction.EDIT_RECONSTRUCTION):
        controller.replace_sample_reconstruction(sample.id, updated)


class TestAChannelEditHoldsOneChannel:
    """An entry a channel edit leaves holds the instructions of the channel the edit rebuilt, and shares
    every other channel with the entries beside it.

    The reference is what copying the whole document leaves allocated, which is what an entry held
    while a snapshot copied the document. A reading near the whole document is an entry holding
    channels its edit left alone.
    """

    def test_an_entry_holds_one_channels_share_of_the_document(
        self,
        arranged: ProjectController,
        history: HistoryManager,
        document: Reconstruction,
    ) -> None:
        channels = ChannelName.items()
        whole = retained_bytes(lambda: copy.deepcopy(document))

        def edits() -> None:
            for edit in range(EDITS):
                channel_name = channels[edit % len(channels)]
                rebuilt = _rebuilt_channel(_sample(arranged).reconstruction, channel_name)
                _land(arranged, history, channel_name, rebuilt)

        per_entry = retained_bytes(edits) / EDITS
        share = whole / len(channels)

        assert per_entry < share * SHARE_MARGIN, (
            f"an entry {per_entry / BYTES_PER_MEGABYTE:.2f} MB, "
            f"a channel's share {share / BYTES_PER_MEGABYTE:.2f} MB"
        )


class TestAChannelEditLandsAtOneChannelsCost:
    """Landing a channel edit builds the document around the one channel the edit rebuilt, and the
    history keeps the document it lands.

    The reference is copying the whole document, which is what a rebuild paid while it copied the
    document to write one channel into it. Landing stays under one channel's share of that copy.
    """

    def test_landing_costs_one_channels_share_of_a_copy(
        self,
        arranged: ProjectController,
        history: HistoryManager,
        document: Reconstruction,
    ) -> None:
        rebuilt = _rebuilt_channel(document, EDITED_CHANNEL)

        copying = seconds(lambda: copy.deepcopy(document))
        landing = seconds(lambda: _land(arranged, history, EDITED_CHANNEL, rebuilt))
        share = copying / len(ChannelName.items())

        assert landing < share, f"landing {landing:.4f} s, a channel's share of a copy {share:.4f} s"
