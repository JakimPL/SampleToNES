from unittest.mock import patch

import pytest

from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.utils.callbacks.queue import CallbackQueue


@pytest.fixture(autouse=True)
def synchronous_queue():
    with patch.object(
        CallbackQueue,
        "add",
        side_effect=lambda callback, *args, priority=0, delay=0, **kwargs: callback(*args),
    ):
        yield


@pytest.fixture
def scheduling() -> SchedulingBehavior:
    return SchedulingBehavior(
        delay_gui_action=0,
        delay_schedule=0,
        delay_cancel=0,
        priority_update_status=0,
        priority_gui_action=0,
        priority_schedule=0,
        priority_add_handler=0,
        priority_add_node=0,
    )
