from collections import Counter
from typing import Dict, Final, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg

ANY_KEY: Final[int] = 0
ANY_BUTTON: Final[int] = -1


class InputWitness:
    """What Dear ImGui counted of the display's input: each release of a key or a button, and each double-click.

    It is a global handler registry of its own in the application's DearPyGui context, so its counts grow as
    the application's frames read the input, and a count stays once a press has come and gone. A hand reads
    them to confirm a press that stood down for a single frame. Every call runs on the render thread, and the
    first call puts the registry in place.
    """

    def __init__(self) -> None:
        self._registry: Optional[Union[int, str]] = None
        self._key_releases: Counter[int] = Counter()
        self._button_release_times: Dict[int, List[float]] = {}
        self._double_clicks: Counter[int] = Counter()

    def key_releases(self, key: int) -> int:
        """How many times Dear ImGui read the Dear ImGui key ``key`` coming up."""
        self._install()
        return self._key_releases[key]

    def button_releases(self, button: int) -> int:
        """How many times Dear ImGui read the Dear ImGui mouse button ``button`` coming up."""
        self._install()
        return len(self._button_release_times.get(button, ()))

    def button_release_times(self, button: int) -> Tuple[float, ...]:
        """The application's clock at each release of the Dear ImGui mouse button ``button``, oldest first."""
        self._install()
        return tuple(self._button_release_times.get(button, ()))

    def double_clicks(self, button: int) -> int:
        """How many double-clicks Dear ImGui counted with the Dear ImGui mouse button ``button``."""
        self._install()
        return self._double_clicks[button]

    def _install(self) -> None:
        if self._registry is not None and dpg.does_item_exist(self._registry):
            return

        with dpg.handler_registry() as registry:
            dpg.add_key_release_handler(key=ANY_KEY, callback=self._on_key_released)
            dpg.add_mouse_release_handler(button=ANY_BUTTON, callback=self._on_button_released)
            dpg.add_mouse_double_click_handler(button=ANY_BUTTON, callback=self._on_double_clicked)
        self._registry = registry

    def _on_key_released(self, _sender: Union[int, str], key: int) -> None:
        self._key_releases[key] += 1

    def _on_button_released(self, _sender: Union[int, str], button: int) -> None:
        self._button_release_times.setdefault(button, []).append(float(dpg.get_total_time()))

    def _on_double_clicked(self, _sender: Union[int, str], button: int) -> None:
        self._double_clicks[button] += 1
