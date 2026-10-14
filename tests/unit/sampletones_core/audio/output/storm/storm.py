import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Final, List, Optional, Tuple

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.output import AudioOutput, OutputSettings, Playback
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE
from tests.suite.audio.machine import HEADPHONES, SPEAKERS, ticking_machine
from tests.unit.sampletones_core.audio.output.harness import QueuedPost, wait_until

from .faults import DeviceFaults
from .owner import Stage, StormOwner
from .record import Checkpoint, StormRecord
from .source import StormMark

OWNERS: Final[int] = 3
ROUNDS: Final[int] = 6
ACTIONS_PER_ROUND: Final[int] = 20
SPEAKERS_INDEX: Final[int] = 0
BARRIER_SECONDS: Final[float] = 10.0
CLOSE_SECONDS: Final[float] = 5.0
OWNER_THREADS: Final[str] = "StormOwner"

Claim = Tuple[int, Optional[Playback[StormMark]]]


class Storm:
    """Owners acting on one output at once, at random, over a device that is slow and fails now and then.

    The first owner also stands for the render thread: it drains the reports between its actions. The owners
    act in rounds, and each round ends at a barrier where the output quiesces: every sound stops, the faults
    are disarmed, the writer ends and every report lands. The owners then claim the output at once, and the
    record keeps which claims held it. Once the last round is over, the output closes for good.
    """

    def __init__(self, seed: int) -> None:
        self.system = ticking_machine((SPEAKERS, HEADPHONES), default_device=SPEAKERS_INDEX)
        self.post = QueuedPost()
        self.output = AudioOutput(self.system.driver, post=self.post)
        settings = _default_settings(self.output.catalog)
        self.record = StormRecord(seed, catalog=self.output.catalog, settings=settings)
        self.output.configure(settings)
        self._faults = DeviceFaults(random.Random(seed), self.system.hooks)
        stage = Stage(output=self.output, system=self.system, record=self.record)
        self._owners = [
            StormOwner(f"owner {index}", seed=seed * OWNERS + index, stage=stage) for index in range(OWNERS)
        ]
        self._barrier = threading.Barrier(OWNERS, timeout=BARRIER_SECONDS)
        self._claims: List[Claim] = [(0, None)] * OWNERS

    def run(self) -> None:
        """Runs every round, quiesces the output, and closes it."""
        with ThreadPoolExecutor(max_workers=OWNERS, thread_name_prefix=OWNER_THREADS) as executor:
            futures = [executor.submit(self._drive, index) for index in range(OWNERS)]
            for future in as_completed(futures):
                future.result()

        self._quiesce()
        self.output.close(deadline_seconds=CLOSE_SECONDS)
        self.post.drain()

    def _drive(self, index: int) -> None:
        """One owner's rounds; an owner that fails breaks the barrier, so the others stop at the next one."""
        owner = self._owners[index]
        leading = index == 0
        finished = False
        try:
            for _ in range(ROUNDS):
                self._act(owner, leading=leading)
                self._claim_together(index, owner, leading=leading)

            finished = True
        finally:
            if not finished:
                self._barrier.abort()

    def _act(self, owner: StormOwner, *, leading: bool) -> None:
        for _ in range(ACTIONS_PER_ROUND):
            owner.act()
            if leading:
                self.post.drain()

            owner.rest()

    def _claim_together(self, index: int, owner: StormOwner, *, leading: bool) -> None:
        self._barrier.wait()
        if leading:
            self._quiesce()

        self._barrier.wait()
        self._claims[index] = owner.claim_at_once()
        self._barrier.wait()
        if leading:
            self.record.checkpoint(
                Checkpoint(
                    ranks=tuple(rank for rank, _ in self._claims),
                    held=tuple(None if playback is None else playback.engaged for _, playback in self._claims),
                )
            )
            self._faults.arm()

        self._barrier.wait()

    def _quiesce(self) -> None:
        """Stops every sound and puts the default device in force, over a device answering every call."""
        self._faults.disarm()
        self.output.stop_all()
        self._settle()
        settings = _default_settings(self.record.catalog)
        self.record.configured(settings)
        self.output.configure(settings)
        self._settle()

    def _settle(self) -> None:
        """Waits until the writer has ended, with every report landed."""
        wait_until(lambda: not self.output.threads.join(deadline_seconds=0.0), self.post, what="the writer to end")
        self.post.drain()


def _default_settings(catalog: DeviceCatalog) -> OutputSettings:
    return OutputSettings(device=catalog.default_device(), buffer_size=DEFAULT_BUFFER_SIZE)
