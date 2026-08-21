from typing import Dict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.session import AssignmentSession
from sampletones_core.reconstructions.reconstructor.stems.assignment.validation import validate_stems_config
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment


def assign_frame(
    fragment: Fragment,
    stems_config: StemsConfig,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    extractor: FeatureExtractor,
    lattice_width: int,
) -> StemFrameAssignment:
    """
    Assigns one target frame's channels to stems, one pick at a time.

    Every pick scores each eligible stem's candidates against the current residual,
    takes the cheapest choice across the active level, subtracts its approximation
    from the residual, and consumes its channel. Levels pick in the hierarchy's
    mode: round-based gives every level's stems one channel per round in level
    order, strict exhausts each level before the next. Each stem holds at most
    the setup's channel cap per frame.

    The frame is answered whole: every covered channel is either picked or reported as
    resting, so a caller records one entry per channel per frame and the streams it
    assembles stay parallel to the frames they describe. Every channel leaves the frame
    with a column of alternatives ``lattice_width`` wide, which is what the decoder
    reading the frames chooses its stream from.

    Args:
        fragment: The frame to assign, matching the matcher and extractor feature
            space.
        stems_config: The stems setup the assignment runs under.
        channels: The enabled channels with their generators.
        matcher: The candidate scoring machinery.
        extractor: The feature extractor whose subtraction forms the residual.
        lattice_width: How many alternatives per channel the decoder reads.

    Returns:
        The picks in the order they were made, together with the channels left resting.

    Raises:
        ValueError: If a stem allows a channel the enabled channels lack.
    """
    validate_stems_config(stems_config, channels)
    session = AssignmentSession(
        fragment,
        stems_config,
        channels,
        matcher,
        extractor,
        lattice_width,
    )
    return session.run()
