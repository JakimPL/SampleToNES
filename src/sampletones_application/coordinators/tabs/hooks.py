from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from sampletones_shared.types.callback import PathCallback, VoidCallback


@dataclass(frozen=True)
class MainTabHooks:
    """What the Main tab reports to the application around it, and what it asks of it.

    The tab answers for its own panels and logic; everything that reaches past them — loading a
    reconstruction, refreshing the browsers of other tabs, asking whether another exclusive
    operation is running — travels here, so the tab's own wiring reads as one collaborator rather
    than as a dozen loose arguments.
    """

    is_operation_active: Callable[[], bool]
    on_busy_state_changed: VoidCallback
    on_reconstruct_file: PathCallback
    on_reconstruct_directory: PathCallback
    on_load_reconstruction: Callable[[Optional[Path]], None]
    on_load_library: PathCallback
    on_load_file: PathCallback
    on_load_directory: VoidCallback
    on_canceled: VoidCallback
    on_refresh_trees: VoidCallback
    on_generate_library: VoidCallback
