from enum import StrEnum


class Work(StrEnum):
    """What the open document's line is busy with, which the waveform's fade names.

    An edit on its way rebuilds the document, and a change to what is heard, or a document just
    opened, has its sound rendered. The reader sees one fade for both and reads from its words
    which of the two the waveform waits for.
    """

    REBUILDING = "rebuilding"
    READING = "reading"
