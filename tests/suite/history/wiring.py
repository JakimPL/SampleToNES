from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController


def wired_history(
    controller: ProjectController,
    *,
    budget: int,
    strict: bool,
) -> HistoryManager:
    """A history over ``controller``, wired the way the composition root wires it.

    Every mutation reaches the history as it lands, so under ``strict`` one outside a
    transaction raises, and every save marks the save point.
    """
    history = HistoryManager(controller, budget=budget, strict=strict)
    controller.on_mutation = history.handle_mutation
    controller.on_saved = history.mark_saved
    return history
