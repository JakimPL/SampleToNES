from pydantic import BaseModel, Field

from sampletones_shared.constants.general import BYTES_PER_MEGABYTE


class RenderingBehavior(BaseModel, extra="forbid", frozen=True):
    cache_megabytes: int = Field(..., ge=1)

    @property
    def cache_bytes(self) -> int:
        """The bytes the render cache keeps audio within before it lets the renders read longest ago go."""
        return self.cache_megabytes * BYTES_PER_MEGABYTE
