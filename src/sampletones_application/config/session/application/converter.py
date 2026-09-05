from pydantic import BaseModel, ConfigDict, Field, field_serializer

from sampletones_core.constants.enums import DEFAULT_CHANNELS, bending_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.types.data import SerializedData


def _starting_settings() -> StemSettings:
    return StemSettings(
        channels=list(DEFAULT_CHANNELS),
        bends=bending_channels(list(DEFAULT_CHANNELS)),
    )


class ConverterConfig(BaseModel):
    """What the converter starts a recording from, carried between runs.

    A recording joins the conversion holding these settings, and the reader then says otherwise for
    it alone. Keeping them as one value is what lets a further per-recording choice reach the
    settings file, the list and the reconstruction record in the same step.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: StemSettings = Field(
        default_factory=_starting_settings,
        description="The settings a recording is given when it joins the conversion.",
    )

    @field_serializer("settings")
    def serialize_settings(self, settings: StemSettings) -> SerializedData:
        """Writes each channel as the plain word it names, which is what the settings file carries."""
        return settings.model_dump(mode="json")
