from typing import Final

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.decoder.base import Lattices, Streams
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate
from sampletones_tools.calibration.trace import TraceRecorder

LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=2)
SILENT: Final[PulseInstruction] = PulseInstruction(on=False, pitch=69, volume=0, duty_cycle=2)
FRAME_LENGTH: Final[int] = 8
BINS: Final[int] = 4


def _scored(instruction: PulseInstruction) -> ScoredCandidate:
    return ScoredCandidate(
        instruction=instruction,
        cost=0.0,
        contribution=Contribution.silence(BINS, FRAME_LENGTH),
    )


class TestTraceRecorder:
    def test_the_trace_keeps_each_column_s_instructions_and_the_decoded_ones(self) -> None:
        lattices: Lattices = {ChannelName.PULSE1: [(_scored(LEAD), _scored(SILENT))] * 2}
        streams: Streams = {ChannelName.PULSE1: [_scored(LEAD), _scored(SILENT)]}
        recorder = TraceRecorder()

        recorder.assigned(lattices)
        recorder.decoded(streams)

        trace = recorder.trace
        assert trace is not None
        assert trace.columns == {ChannelName.PULSE1: ((LEAD, SILENT), (LEAD, SILENT))}
        assert trace.decoded == {ChannelName.PULSE1: (LEAD, SILENT)}

    def test_a_search_heard_short_of_its_decoding_leaves_no_trace(self) -> None:
        recorder = TraceRecorder()

        recorder.assigned({ChannelName.PULSE1: [(_scored(LEAD),)]})

        assert recorder.trace is None
