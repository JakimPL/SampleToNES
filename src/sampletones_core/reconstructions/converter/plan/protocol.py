from typing import List, Protocol

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
