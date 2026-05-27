from pathlib import Path

from pydantic import BaseModel


class AdvancedSettingsPanelViewModel(BaseModel, frozen=True):
    max_workers: int
    library_directory: Path
    output_directory: Path
