from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class GraphColors(BaseModel, extra="forbid", frozen=True):
    bar_plot: WrittenColor
    waveform_sample: WrittenColor
    waveform_reconstruction: WrittenColor
