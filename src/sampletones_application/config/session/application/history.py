from typing import Final

from pydantic import BaseModel, Field

DEFAULT_HISTORY_BUDGET: Final[int] = 500


class HistoryConfig(BaseModel):
    """Persisted history preferences.

    ``budget`` caps how many undo entries the session keeps; once exceeded, the
    oldest entries are evicted. It is a user-facing preference, so it lives with
    the application configuration and survives across sessions.
    """

    budget: int = Field(
        default=DEFAULT_HISTORY_BUDGET,
        description="Maximum number of undo entries retained per session.",
    )
