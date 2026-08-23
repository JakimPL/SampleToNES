from sampletones_application.categories.abstract import AbstractElement


class ConverterStemMoveElements(AbstractElement):
    """The moves a gathered recording can make, as the row's menu names them."""

    CONTEXT_MOVE_UP = "context_move_up"
    CONTEXT_MOVE_DOWN = "context_move_down"
    CONTEXT_JOIN_ABOVE = "context_join_above"
    CONTEXT_JOIN_BELOW = "context_join_below"
    CONTEXT_ISOLATE = "context_isolate"
    CONTEXT_REMOVE_STEM = "context_remove_stem"
