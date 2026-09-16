from typing import Dict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.session import AssignmentSession
from sampletones_core.reconstructions.reconstructor.stems.assignment.validation import validate_stems_config
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment


def assign_frame(
    fragments: Dict[int, Fragment],
    stems_config: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    lattice_width: int,
) -> StemFrameAssignment:
    """
    Assigns one frame's channels to stems, one pick at a time, for as long as a pick helps.

    Every pick scores each stem's candidates by the cost that stem's own frame reaches with the
    candidate sounding beside the stem's earlier picks, silence among them, and takes the channel
    whose best candidate lowers a frame's cost the most, weighted by the energy of that frame.
    Picks stop when no candidate lowers any frame's cost, so a frame one channel renders whole
    sounds one channel. Scoring each stem against its own recording is what makes the channel a
    stem wins carry that recording's sound. Levels pick in the hierarchy's mode: round-based gives
    every level's stems one channel per round in level order, strict exhausts each level before
    the next. Each stem holds at most the count its own settings allow per frame.

    A channel no pick took goes to the first sounding stem that may hold it, headed by its silence,
    and every choice is then scored once more with the stem's other choices sounding. The frame is
    answered whole: every covered channel is held or reported as resting, so a caller records one
    entry per channel per frame and the streams it assembles stay parallel to the frames they
    describe. Every channel leaves the frame with a column of alternatives ``lattice_width`` wide,
    which is what the decoder reading the frames chooses its stream from.

    Args:
        fragments: This frame of every stem, keyed by stem id, in the matcher's feature space.
        stems_config: The stems setup the assignment runs under.
        channels: The enabled channels with their generators.
        matcher: The candidate scoring machinery.
        lattice_width: How many alternatives per channel the decoder reads.

    Returns:
        The picks in the order they were made, together with the channels left resting.

    Raises:
        ValueError: If a stem allows a channel the enabled channels lack.
    """
    validate_stems_config(stems_config, channels)
    session = AssignmentSession(
        fragments,
        stems_config,
        channels,
        matcher,
        lattice_width,
    )
    return session.run()
