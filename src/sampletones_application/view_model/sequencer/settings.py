from pydantic import BaseModel


class SequencerSettingsViewModel(BaseModel, frozen=True):
    """Module-options inputs for the sequencer grid, sourced from the project.

    The project ``settings`` are the document of record for these values; the
    sequencer reads them from here rather than from the application config so the
    grid always reflects the open project.
    """

    change_rate: int
    tempo: int
    speed: int
    rows_per_pattern: int
