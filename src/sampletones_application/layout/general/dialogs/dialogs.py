from pydantic import BaseModel

from sampletones_application.layout.general.dialogs.about import AboutDialogLayout
from sampletones_application.layout.primitives import DialogGeometry


class DialogsLayout(BaseModel, extra="forbid", frozen=True):
    """The dialogs a reader is answered by, each stating the size it opens at.

    ``traceback_height`` is the height the traceback's text box takes once a reader unfolds it,
    which the dialog holding it grows to make room for.
    """

    default: DialogGeometry
    error: DialogGeometry
    recovery: DialogGeometry
    confirmation: DialogGeometry
    traceback_height: int
    about: AboutDialogLayout
