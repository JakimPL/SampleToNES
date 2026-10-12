from typing import Mapping

import numpy as np

from sampletones_application.logic.shared.renders import RenderCache
from sampletones_core.audio import mix
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from sampletones_core.reconstructions.reconstruction.stems.hearing import Hearing, heard_renders


def warmed(
    renders: RenderCache,
    reconstruction: Reconstruction,
    hearing: Hearing,
    recordings: Mapping[int, np.ndarray],
) -> None:
    """Keeps in ``renders`` what the worker would hand back for ``hearing`` of ``reconstruction``, the mix of the
    recordings heard included.

    A case driving the panel logic alone has no worker to render what the reader hears, so it
    keeps the renders the way a landing does, and the panel reads them as it reads any kept sound.
    """
    channels = rendered_channels(reconstruction)
    mixed = rendered_mix(reconstruction)
    renders.adopt(reconstruction, channels, mixed)
    renders.adopt_heard(reconstruction, hearing, heard_renders(reconstruction, hearing, channels, mixed))
    heard = hearing.selection.any_channel()
    mixed_from = [recording for stem_id, recording in recordings.items() if stem_id in heard]
    if mixed_from:
        renders.adopt_original(mixed_from, reconstruction.config, mix(mixed_from))
