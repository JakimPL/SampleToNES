from dataclasses import dataclass

from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class RetunedSample:
    """A sample's reconstruction re-synthesized to a new NES frequency.

    Carries the ``voice_id`` so the caller can swap the retuned reconstruction into
    the right project sample as each result arrives, and the ``source`` it was retuned
    from, so the caller can tell whether the sample still holds it.

    Attributes:
        voice_id: The sample the retune is for.
        reconstruction: The reconstruction at the new frequency.
        source: The reconstruction the sample held when the batch started, which the retune
            was computed from.
    """

    voice_id: str
    reconstruction: Reconstruction
    source: Reconstruction
