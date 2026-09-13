from pathlib import Path
from typing import Dict, List, Optional


class RecordedApplication:
    """A stand-in for the application launcher that records what each start was given."""

    def __init__(self) -> None:
        self.starts: List[Dict[str, Optional[Path]]] = []

    def __call__(
        self,
        config_path: Optional[Path] = None,
        *,
        library_path: Optional[Path] = None,
        reconstruction_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> None:
        self.starts.append(
            {
                "config": config_path,
                "library": library_path,
                "reconstruction": reconstruction_path,
                "project": project_path,
            }
        )
