from dataclasses import dataclass

from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class RetunedSample:
    """A sample's reconstruction re-synthesized to a new NES frequency.

    Carries the ``sample_id`` so the caller can swap the retuned reconstruction into
    the right project sample as each result arrives.
    """

    sample_id: str
    reconstruction: Reconstruction
