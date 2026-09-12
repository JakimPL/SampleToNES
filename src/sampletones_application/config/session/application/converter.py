from pydantic import BaseModel, ConfigDict, Field, field_serializer

from sampletones_application.constants.output import OutputKind
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    HierarchyMode,
    bending_channels,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.types.data import SerializedData


def _starting_settings() -> StemSettings:
    return StemSettings(
        channels=list(DEFAULT_CHANNELS),
        bends=bending_channels(list(DEFAULT_CHANNELS)),
    )


class ConverterConfig(BaseModel):
    """How the converter opens, carried between runs.

    A recording joins the conversion holding ``settings``, and the reader then says otherwise for
    it alone. Keeping those as one value is what lets a further per-recording choice reach the
    settings file, the list and the reconstruction record in the same step.

    The rest name the shape of the run itself, so a launch opens on the run the reader last set up
    rather than on the shipped one.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: StemSettings = Field(
        default_factory=_starting_settings,
        description="The settings a recording is given when it joins the conversion.",
    )

    output: OutputKind = Field(
        default=OutputKind.PER_RECORDING,
        description="Whether a run writes one reconstruction per recording or one from them all.",
    )
    channel_cap: int = Field(
        default=len(ChannelName),
        description="How many channels one recording may hold in a single frame.",
    )
    hierarchy_mode: HierarchyMode = Field(
        default=DEFAULT_STEMS_HIERARCHY_MODE,
        description="How the levels of a mix take turns choosing.",
    )

    @field_serializer("settings")
    def serialize_settings(self, settings: StemSettings) -> SerializedData:
        """Writes each channel as the plain word it names, which is what the settings file carries."""
        return settings.model_dump(mode="json")

    @field_serializer("output")
    def serialize_output(self, output: OutputKind) -> str:
        """Writes the kind as the plain word it names, which is what the settings file carries."""
        return output.value

    @field_serializer("hierarchy_mode")
    def serialize_hierarchy_mode(self, hierarchy_mode: HierarchyMode) -> str:
        """Writes the mode as the plain word it names, which is what the settings file carries."""
        return hierarchy_mode.value
