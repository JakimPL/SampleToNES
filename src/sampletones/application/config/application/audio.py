from pydantic import BaseModel, ConfigDict, Field

from sampletones.audio import AudioDeviceManager, CurrentDevice
from sampletones.constants.audio import DEFAULT_BUFFER_SIZE, BufferSize


class AudioConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_device: CurrentDevice = Field(
        default_factory=CurrentDevice.default,
        description="The index of the selected audio device.",
    )
    buffer_size: BufferSize = Field(
        default=DEFAULT_BUFFER_SIZE,
        description="The audio buffer size in samples.",
    )
    volume: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="The master volume level (0.0 to 1.0).",
    )

    def set_audio_settings(self, audio_device_manager: AudioDeviceManager) -> None:
        self.buffer_size = audio_device_manager.buffer_size
        self.current_device = audio_device_manager.get_current_device()
