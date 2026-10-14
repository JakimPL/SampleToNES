from typing import Final, List

from .rig import PlaybackRig

THREAD_DEADLINE_SECONDS: Final[float] = 5.0


def check_after(rig: PlaybackRig, *, strict: bool) -> None:
    """Holds a case's whole run to what every playback owes the device, once the case is done with it.

    The rig is torn down first where the case left it running, so every case ends the way a quit does. Then
    no stream is left open, the device never held two at once, nothing reached a closed stream or a
    terminated backend, every audio thread has ended, nothing escaped a thread, and the application logged
    no error a case did not cause on purpose. A case that failed has already said what broke, often the very
    rule checked here, so for it the findings are printed beside the failure.

    Args:
        rig: The rig the case drove.
        strict: Whether a finding fails the case, which holds for a case that passed.

    Raises:
        AssertionError: Naming each rule the run broke, with the whole picture.
    """
    try:
        rig.teardown()
        rig.drain()
        survivors = rig.threads.join_audio_threads(deadline_seconds=THREAD_DEADLINE_SECONDS)
        broken = _broken_rules(rig, [thread.name for thread in survivors])
    finally:
        rig.errors.detach()

    findings = "\n".join(broken) + "\n" + rig.describe()
    if not strict:
        if broken:
            print(f"after-check findings:\n{findings}")

        return

    assert not broken, findings


def _broken_rules(rig: PlaybackRig, survivors: List[str]) -> List[str]:
    broken: List[str] = []
    if rig.timeline.open_streams():
        broken.append(f"streams left open: {sorted(rig.timeline.open_streams())}")

    if rig.timeline.most_streams_open() > 1:
        broken.append(f"the device held {rig.timeline.most_streams_open()} streams at once")

    if rig.timeline.violations():
        broken.append(f"device misuse: {rig.timeline.violations()}")

    if survivors:
        broken.append(f"audio threads alive after teardown: {survivors}")

    if rig.threads.escaped:
        broken.append(f"escaped a thread: {rig.threads.escaped!r}")

    if rig.errors.messages and not rig.expects_errors:
        broken.append(f"errors logged: {rig.errors.messages}")

    return broken
