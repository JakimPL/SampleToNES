from typing import Dict, Final, FrozenSet, List, Set, Tuple, Type

from sampletones_core.audio.output import AudioOutput, EndCause
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError
from tests.suite.audio.machine import FakeAudioSystem
from tests.suite.audio.timeline import Drained, Timeline

from .listener import LandedEnd
from .record import StormRecord
from .source import StormFailure
from .written import WrittenSounds

FORESEEN_FAILURES: Final[Tuple[Type[Exception], ...]] = (StormFailure, PlaybackError, NoOutputDeviceError)
CUT_CAUSES: Final[FrozenSet[EndCause]] = frozenset({EndCause.STOPPED, EndCause.TAKEN})


def broken_rules(record: StormRecord, system: FakeAudioSystem, output: AudioOutput) -> List[str]:
    """Every break of the output contract the storm left, each named by its rule; empty where none broke."""
    writes = WrittenSounds.read(system.timeline.events())
    return [
        *_claims(record),
        *_device(system.timeline, writes),
        *_endings(record, writes),
        *_positions(record, writes),
        *_cuts(record, system.timeline, writes),
        *_teardown(system, output),
    ]


def causes(record: StormRecord) -> Set[EndCause]:
    """Every cause an end report of the storm named."""
    return {landed.ending.cause for sounding in record.soundings for landed in sounding.listener.endings}


def _claims(record: StormRecord) -> List[str]:
    """Rule 1: claims made at once leave one holder, the highest ranked, and decline only those below it."""
    broken: List[str] = []
    for number, checkpoint in enumerate(record.checkpoints):
        top = max(checkpoint.ranks)
        holders = [rank for rank, held in zip(checkpoint.ranks, checkpoint.held) if held is True]
        declined = [rank for rank, held in zip(checkpoint.ranks, checkpoint.held) if held is None]
        if len(holders) != 1:
            broken.append(f"Rule 1: claims {checkpoint.ranks} at checkpoint {number} left {len(holders)} holders")
        elif holders[0] != top:
            broken.append(f"Rule 1: a claim at rank {holders[0]} held the output over one at rank {top}")

        if any(rank >= top for rank in declined):
            broken.append(f"Rule 1: claims {checkpoint.ranks} at checkpoint {number} declined one at the top rank")

    return broken


def _device(timeline: Timeline, writes: WrittenSounds) -> List[str]:
    """Rules 1 and 2: the device holds one stream at a time, used as a correct playback uses it, for one sound."""
    broken = [f"Rule 2: the device met {kind.value}" for kind in timeline.violations()]
    if timeline.most_streams_open() > 1:
        broken.append(f"Rule 2: the device held {timeline.most_streams_open()} streams open at once")

    return [*broken, *(f"Rule 1: {stray}" for stray in writes.strays)]


def _endings(record: StormRecord, writes: WrittenSounds) -> List[str]:
    """Rules 3 and 7: one end report each, landing once the sound let the output go and its last block played."""
    broken: List[str] = []
    for sounding in record.soundings:
        identity = sounding.listener.sound.identity
        endings = sounding.listener.endings
        if len(endings) != 1:
            broken.append(f"Rule 3: sound {identity} sent {len(endings)} end reports")

        for landed in endings:
            broken.extend(_ending(identity, landed, writes))

    return broken


def _ending(identity: int, landed: LandedEnd, writes: WrittenSounds) -> List[str]:
    broken: List[str] = []
    if landed.engaged:
        broken.append(f"Rule 3: sound {identity} still held the output as its end report landed")

    written_after = writes.after(identity, landed.index)
    if written_after:
        broken.append(f"Rule 3: sound {identity} had {written_after} blocks written after its end report landed")

    error = landed.ending.error
    if error is not None and not isinstance(error, FORESEEN_FAILURES):
        broken.append(f"Rule 7: sound {identity} failed with an unforeseen {error!r}")

    return broken


def _positions(record: StormRecord, writes: WrittenSounds) -> List[str]:
    """Rule 4: positions land in order, for blocks the device took, after the seek before them, before the end."""
    broken: List[str] = []
    for sounding in record.soundings:
        identity = sounding.listener.sound.identity
        serial = 0
        for landed in sounding.listener.marks:
            if landed.after_end:
                broken.append(f"Rule 4: sound {identity} reported block {landed.mark.serial} after its end")

            if landed.mark.serial <= serial:
                broken.append(f"Rule 4: sound {identity} reported block {landed.mark.serial} after block {serial}")

            if landed.mark.position < landed.sought:
                broken.append(
                    f"Rule 4: sound {identity} reported frame {landed.mark.position} after a seek to {landed.sought}"
                )

            written = writes.before(identity, landed.index)
            if landed.mark.serial > written:
                broken.append(
                    f"Rule 4: sound {identity} reported block {landed.mark.serial} with {written} of its blocks played"
                )

            serial = landed.mark.serial

    return broken


def _cuts(record: StormRecord, timeline: Timeline, writes: WrittenSounds) -> List[str]:
    """Rule 6: a sound stopped or taken over is cut, so the stream it played on never plays its tail out."""
    endings: Dict[int, List[LandedEnd]] = {
        sounding.listener.sound.identity: sounding.listener.endings for sounding in record.soundings
    }
    broken: List[str] = []
    for stream in sorted({event.stream for event in timeline.of(Drained)}):
        for identity in sorted(writes.carried.get(stream, set())):
            for landed in endings.get(identity, []):
                if landed.ending.cause in CUT_CAUSES:
                    broken.append(
                        f"Rule 6: stream {stream} played out the tail of sound {identity}, "
                        f"which ended {landed.ending.cause.value}"
                    )

    return broken


def _teardown(system: FakeAudioSystem, output: AudioOutput) -> List[str]:
    """Rule 8: once the output closed, no audio thread runs, no stream is open, and every backend is terminated."""
    broken = [f"Rule 8: {thread.name} outlived the teardown" for thread in output.threads.join(deadline_seconds=0.0)]
    if system.has_open_streams():
        broken.append("Rule 8: a stream stayed open after the teardown")

    running = [driver.index for driver in system.drivers if not driver.terminated]
    if running:
        broken.append(f"Rule 8: backend instances {running} were left running")

    return broken
