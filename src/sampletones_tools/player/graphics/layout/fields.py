from pydantic import BaseModel, ConfigDict, Field

from sampletones_tools.player.graphics.layout.cells import Column, Row


class TextField(BaseModel):
    """Where one line of the program's text is written.

    Attributes:
        row: The row the line lies in.
        column: The cell the line starts at.
        width: The cells the line spans.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    row: Row
    column: Column
    width: int = Field(ge=1)


class ProgramFields(BaseModel):
    """Where the program's three lines of text are written.

    Attributes:
        title: The line holding the title.
        artist: The line holding the artist.
        copyright: The line holding the copyright.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: TextField
    artist: TextField
    copyright: TextField


class TransportFields(BaseModel):
    """Where the playing state and the two times are written.

    Attributes:
        row: The row all three lie in.
        state_column: The cell showing whether the song plays, waits or has ended.
        played_column: The first cell of the time played so far.
        total_column: The first cell of the song's whole length.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    row: Row
    state_column: Column
    played_column: Column
    total_column: Column


class ProgressField(BaseModel):
    """Where the progress bar lies.

    Attributes:
        row: The bar's row.
        column: The bar's leftmost cell.
        width: The cells the bar spans.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    row: Row
    column: Column
    width: int = Field(ge=1)


class ChannelFields(BaseModel):
    """Where each channel's wave shape, note and level meter are written.

    A channel takes two rows of cells, named by the upper one. The columns are shared, so the four
    channels read as one table.

    Attributes:
        wave_column: The leftmost cell of the wave shape.
        note_column: The first cell of the note.
        meter_column: The first cell of the level meter.
        pulse1_row: The upper row of the first pulse channel.
        pulse2_row: The upper row of the second pulse channel.
        triangle_row: The upper row of the triangle channel.
        noise_row: The upper row of the noise channel.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    wave_column: Column
    note_column: Column
    meter_column: Column
    pulse1_row: Row
    pulse2_row: Row
    triangle_row: Row
    noise_row: Row


class KeyboardFields(BaseModel):
    """Where the keyboard lies and where the markers above it move.

    Attributes:
        lane_row: The row the markers move along.
        key_row: The row of the keys.
        column: The cell holding the lowest key.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    lane_row: Row
    key_row: Row
    column: Column
