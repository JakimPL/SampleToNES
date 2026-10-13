import weakref
from collections import OrderedDict
from typing import Final, Tuple

import numpy as np

from sampletones_core.audio import minmax_decimate

KEPT_DECIMATIONS: Final[int] = 8

Points = Tuple[np.ndarray, np.ndarray]


class Decimations:
    """The points a display draws an array as, kept by the array's identity for as long as the array lives.

    A render the cache keeps is read-only and keeps its identity for as long as the cache holds it,
    so the min-max reduction a display draws it as is made once and read back on every showing. A
    reduction goes when its array is collected, before the identity can name another, and the
    reductions read longest ago go first beyond a small number kept, so the memo holds the few
    arrays a display shows. The reduction keeps every extreme, so the peak of the points is the
    array's own.
    """

    def __init__(self, max_display_points: int) -> None:
        self._max_display_points = max_display_points
        self._points: OrderedDict[int, Points] = OrderedDict()

    def points(self, audio: np.ndarray) -> Points:
        """The positions and the values a display draws ``audio`` as.

        An array longer than the points the display shows reduces to its extremes per bucket; a
        shorter one draws every sample.

        Args:
            audio: The waveform, one-dimensional.

        Returns:
            Points: The positions along the array and the value at each.
        """
        kept = self._points.get(id(audio))
        if kept is not None:
            self._points.move_to_end(id(audio))
            return kept

        points = self._reduced(audio)
        self._points[id(audio)] = points
        weakref.finalize(audio, self._forget, id(audio))
        while len(self._points) > KEPT_DECIMATIONS:
            self._points.popitem(last=False)

        return points

    def _reduced(self, audio: np.ndarray) -> Points:
        values = audio.astype(np.float32, copy=False)
        if values.ndim != 1:
            raise ValueError("A display draws a one-dimensional waveform")

        if values.shape[0] > self._max_display_points:
            return minmax_decimate(values, num_buckets=self._max_display_points)

        return np.arange(values.shape[0], dtype=np.float32), values

    def _forget(self, identity: int) -> None:
        self._points.pop(identity, None)
