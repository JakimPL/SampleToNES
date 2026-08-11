from contextlib import contextmanager
from typing import Iterator

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.dpg import dpg_container
from sampletones_shared.types.application import Sender


def create_stage() -> Sender:
    """Create a detached staging container and return its tag.

    Widgets built into a stage stay off the rendered item tree, so a large
    subtree can be assembled across several frames while layout and drawing wait
    until it is live. :func:`attach_staged_item` moves the finished roots into
    their live parent in one step.
    """
    stage: Sender = dpg.add_stage()
    return stage


@contextmanager
def staged_container(stage: Sender) -> Iterator[None]:
    """Push ``stage`` as the active container so parentless items land in it.

    Items created with an explicit parent still honour that parent; the stage
    captures the parentless ones.
    """
    with dpg_container(stage):
        yield


def attach_staged_item(item: Sender, parent: Sender) -> None:
    """Move a staged item and its subtree under a live parent."""
    if dpg.does_item_exist(item) and dpg.does_item_exist(parent):
        dpg.move_item(item, parent=parent)


def delete_stage(stage: Sender) -> None:
    if dpg.does_item_exist(stage):
        dpg.delete_item(stage)
