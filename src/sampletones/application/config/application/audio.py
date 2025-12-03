from pydantic import BaseModel, ConfigDict, Field

from sampletones.audio import AudioDeviceManager, CurrentDevice


class AudioConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_device: CurrentDevice = Field(
        default_factory=CurrentDevice.default,
        description="The index of the selected audio device.",
    )
    volume: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="The master volume level (0.0 to 1.0).",
    )

    def store_current_device(self, audio_device_manager: AudioDeviceManager) -> None:
        self.current_device = audio_device_manager.get_current_device()
