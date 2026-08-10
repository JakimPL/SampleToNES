from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class HeaderColors(BaseModel, extra="forbid", frozen=True):
    """Colours the tracker's clickable column header takes.

    ``background`` is the band the header row sits in, the shade a table header carries;
    ``hovered`` and ``active`` are the washes a header label takes under the pointer and while
    it is held, which is how the label shows it answers to a click.
    """

    background: WrittenColor
    hovered: WrittenColor
    active: WrittenColor
