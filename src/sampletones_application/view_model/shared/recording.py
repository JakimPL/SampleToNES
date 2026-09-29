from pydantic import BaseModel


class NamedRecordingViewModel(BaseModel, extra="forbid", frozen=True):
    """One recording a document names, as a list of them shows it.

    The id is the entry the recording was converted as, which picks the color it is known by, so
    a mark beside its name reads as the stretches it holds wherever those are drawn.

    Attributes:
        stem_id: The entry the recording was converted as.
        name: What the recording is called.
    """

    stem_id: int
    name: str
