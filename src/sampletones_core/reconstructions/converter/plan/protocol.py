from pathlib import Path
from typing import List, Protocol, Tuple

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.job import ConversionJob


class ConversionPlan(Protocol):
    """What a conversion request amounts to: the reconstructions it builds.

    A plan answers with the jobs the request divides into, in the order they are run, resolved
    against the configuration the run uses, since that is what settles where each reconstruction
    is written. Resolving happens on the converter's own thread, so a plan that reads the
    filesystem does so away from the interface.
    """

    def jobs(self, config: Config) -> List[ConversionJob]: ...

    def existing_targets(self, config: Config) -> Tuple[Path, ...]:
        """The reconstructions already standing where this plan would write.

        A caller asks this ahead of the run, on its own thread, so the answer stays cheap: a
        run that would write over work already done is one the reader gets to answer for. A
        plan that keeps standing files as it goes answers with none, having settled it already.
        """
